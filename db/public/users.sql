create table users
(
    user_id  integer not null
        primary key,
    login    varchar(255),
    password varchar(255)
);

alter table users
    owner to postgres;

