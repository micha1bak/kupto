
-- 1. Tworzenie tabel słownikowych i niezależnych
CREATE TABLE users (
                       user_id SERIAL PRIMARY KEY,
                       login VARCHAR(50) UNIQUE NOT NULL,
                       password VARCHAR(255) NOT NULL -- Miejsce na zahashowane hasło
);

CREATE TABLE category (
                          category_id SERIAL PRIMARY KEY,
                          name VARCHAR(100) UNIQUE NOT NULL
);

-- 2. Tworzenie tabel zależnych od pierwszej warstwy
CREATE TABLE product (
                         product_id SERIAL PRIMARY KEY,
                         category_id INT NOT NULL,
                         name VARCHAR(100) UNIQUE NOT NULL,
                         CONSTRAINT fk_category
                             FOREIGN KEY (category_id)
                                 REFERENCES category (category_id)
                                 ON DELETE RESTRICT -- Nie pozwalamy usunąć kategorii, jeśli są w niej produkty
);

CREATE TABLE list (
                      list_id SERIAL PRIMARY KEY,
                      owner_id INT NOT NULL,
                      name VARCHAR(100) NOT NULL,
                      CONSTRAINT fk_list_owner
                          FOREIGN KEY (owner_id)
                              REFERENCES users(user_id)
                              ON DELETE CASCADE -- Usunięcie użytkownika usunie jego listy
);

CREATE TABLE template (
                          template_id SERIAL PRIMARY KEY,
                          owner_id INT NOT NULL,
                          name VARCHAR(100) NOT NULL,
                          CONSTRAINT fk_template_owner
                              FOREIGN KEY (owner_id)
                                  REFERENCES users(user_id)
                                  ON DELETE CASCADE
);

-- 3. Tworzenie tabel łączących (relacje Wiele-do-Wielu)
CREATE TABLE list_access (
                             list_id INT NOT NULL,
                             user_id INT NOT NULL,
                             PRIMARY KEY (list_id, user_id), -- Klucz złożony z dwóch kolumn
                             CONSTRAINT fk_access_list
                                 FOREIGN KEY (list_id)
                                     REFERENCES list(list_id)
                                     ON DELETE CASCADE,
                             CONSTRAINT fk_access_user
                                 FOREIGN KEY (user_id)
                                     REFERENCES users(user_id)
                                     ON DELETE CASCADE
);

CREATE TABLE list_item (
                           list_id INT NOT NULL,
                           product_id INT NOT NULL,
                           quantity VARCHAR(50),
                           PRIMARY KEY (list_id, product_id),
                           CONSTRAINT fk_item_list
                               FOREIGN KEY (list_id)
                                   REFERENCES list(list_id)
                                   ON DELETE CASCADE,
                           CONSTRAINT fk_item_product
                               FOREIGN KEY (product_id)
                                   REFERENCES product(product_id)
                                   ON DELETE CASCADE
);

CREATE TABLE template_item (
                               template_id INT NOT NULL,
                               product_id INT NOT NULL,
                               quantity VARCHAR(50),
                               PRIMARY KEY (template_id, product_id),
                               CONSTRAINT fk_t_item_template
                                   FOREIGN KEY (template_id)
                                       REFERENCES template(template_id)
                                       ON DELETE CASCADE,
                               CONSTRAINT fk_t_item_product
                                   FOREIGN KEY (product_id)
                                       REFERENCES product(product_id)
                                       ON DELETE CASCADE
);