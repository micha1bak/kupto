create table product
(
    product_id integer not null
        primary key,
    category   integer
        constraint fk_product_category
            references category,
    name       varchar(255)
);

alter table product
    owner to postgres;

