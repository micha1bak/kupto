create view full_shopping_list(id, name, quantity, category, added_by) as
SELECT p.product_id AS id,
       p.name,
       sl.quantity,
       c.name       AS category,
       u.login      AS added_by
FROM shopping_list sl
         JOIN users u ON u.user_id = sl.added_by_user_id
         JOIN product p ON p.product_id = sl.product_id
         JOIN category c ON c.category_id = p.category;

alter table full_shopping_list
    owner to postgres;

