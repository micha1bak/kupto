create table template
(
    template_id integer      not null
        primary key,
    name        varchar(255) not null,
    user_id     integer
        references users
);

alter table template
    owner to postgres;

