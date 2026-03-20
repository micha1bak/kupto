create table shopping_list
(
    product_id       integer not null
        primary key
        constraint fk_shopping_list_product
            references product,
    added_by_user_id integer
        constraint fk_shopping_list_user
            references users,
    quantity         varchar(255)
);

alter table shopping_list
    owner to postgres;

