'use server'

import { query } from '@/lib/db';
import { getSession } from '@/lib/auth';
import { revalidatePath } from 'next/cache';

export type ShoppingListItem = {
  id: number;
  name: string;
  quantity: string | null;
  unit?: string; // v1.0 used quantity as a string often containing unit
};

export type ShoppingListCategoryGroup = {
  category: string;
  items: ShoppingListItem[];
};

export type ProductSuggestion = {
  id: number;
  name: string;
};

export async function getShoppingList(): Promise<ShoppingListCategoryGroup[]> {
  const session = await getSession();

  if (!session) {
    return [];
  }

  const { userId } = session;

  try {
    // Pobieramy produkty z list, do których użytkownik ma dostęp (właściciel lub współdzielona)
    const result = await query(`
      SELECT 
        c.name as category_name,
        p.product_id as id,
        p.name as product_name,
        li.quantity
      FROM list l
      LEFT JOIN list_access la ON l.list_id = la.list_id
      JOIN list_item li ON l.list_id = li.list_id
      JOIN product p ON li.product_id = p.product_id
      JOIN category c ON p.category_id = c.category_id
      WHERE l.owner_id = $1 OR la.user_id = $1
      ORDER BY c.name, p.name
    `, [userId]);

    // Grupowanie danych po kategorii
    const groups: { [key: string]: ShoppingListItem[] } = {};

    result.rows.forEach((row: any) => {
      if (!groups[row.category_name]) {
        groups[row.category_name] = [];
      }
      groups[row.category_name].push({
        id: row.id,
        name: row.product_name,
        quantity: row.quantity,
      });
    });

    return Object.keys(groups).map(category => ({
      category,
      items: groups[category]
    }));
  } catch (error) {
    console.error('Błąd podczas pobierania listy zakupów:', error);
    return [];
  }
}

/**
 * Wyszukuje produkty w bazie dla podpowiedzi.
 */
export async function searchProducts(queryText: string): Promise<ProductSuggestion[]> {
  if (!queryText || queryText.length < 1) return [];

  const session = await getSession();
  if (!session) return [];

  try {
    const result = await query(
      `SELECT product_id as id, name FROM product WHERE name ILIKE $1 LIMIT 5`,
      [`%${queryText}%`]
    );
    return result.rows;
  } catch (error) {
    console.error('Błąd podczas wyszukiwania produktów:', error);
    return [];
  }
}

/**
 * Dodaje produkt do domyślnej listy użytkownika.
 */
export async function addProductToList(productId: number) {
  const session = await getSession();
  if (!session) throw new Error('Unauthorized');

  const { userId } = session;

  try {
    // Znajdź pierwszą dostępną listę (lub stwórz jeśli brak)
    const listResult = await query(
      `SELECT list_id FROM list WHERE owner_id = $1 OR list_id IN (SELECT list_id FROM list_access WHERE user_id = $1) LIMIT 1`,
      [userId]
    );

    let listId;
    if (listResult.rows.length === 0) {
      const newList = await query(
        `INSERT INTO list (owner_id, name) VALUES ($1, $2) RETURNING list_id`,
        [userId, 'Moja Lista']
      );
      listId = newList.rows[0].list_id;
    } else {
      listId = listResult.rows[0].list_id;
    }

    // Dodaj produkt do listy (jeśli już jest, zignoruj conflict)
    await query(
      `INSERT INTO list_item (list_id, product_id, quantity) 
       VALUES ($1, $2, '1') 
       ON CONFLICT (list_id, product_id) DO NOTHING`,
      [listId, productId]
    );

    revalidatePath('/');
    return { success: true };
  } catch (error) {
    console.error('Błąd podczas dodawania produktu do listy:', error);
    throw error;
  }
}
