create table category
(
    category_id integer not null
        primary key,
    name        varchar(255)
);

alter table category
    owner to postgres;

