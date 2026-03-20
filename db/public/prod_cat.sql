create view prod_cat(id, name, category) as
SELECT p.product_id AS id,
       p.name,
       c.name       AS category
FROM product p
         JOIN category c ON p.category = c.category_id;

alter table prod_cat
    owner to postgres;

