'use server'

import { query } from '@/lib/db';
import { getSession } from '@/lib/auth';

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
