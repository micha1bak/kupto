create table template_item
(
    template_id integer not null
        references template,
    product_id  integer not null
        references product,
    quantity    varchar(255),
    primary key (template_id, product_id)
);

alter table template_item
    owner to postgres;

