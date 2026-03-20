--
-- PostgreSQL database dump
--

\restrict xqzqzbtcGodd4a8vDN6BfLoRfKPUrDfdy0IlwDUDeeidHhs8gvrQZMhPEycRiHm

-- Dumped from database version 18.1 (Debian 18.1-1.pgdg13+2)
-- Dumped by pg_dump version 18.1 (Debian 18.1-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: category; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.category (category_id, name) VALUES (6, 'Mięso i wędliny');
INSERT INTO public.category (category_id, name) VALUES (7, 'Napoje');
INSERT INTO public.category (category_id, name) VALUES (8, 'Mrożonki');
INSERT INTO public.category (category_id, name) VALUES (9, 'Węglowodany');
INSERT INTO public.category (category_id, name) VALUES (10, 'Przekąski');
INSERT INTO public.category (category_id, name) VALUES (11, 'Konserwy i słoiki');
INSERT INTO public.category (category_id, name) VALUES (13, 'Kosmetyki i higiena');
INSERT INTO public.category (category_id, name) VALUES (1, 'Warzywa');
INSERT INTO public.category (category_id, name) VALUES (2, 'Owoce');
INSERT INTO public.category (category_id, name) VALUES (3, 'Nabiał');
INSERT INTO public.category (category_id, name) VALUES (4, 'Pieczywo');
INSERT INTO public.category (category_id, name) VALUES (5, 'Słodycze');
INSERT INTO public.category (category_id, name) VALUES (12, 'Chemia');
INSERT INTO public.category (category_id, name) VALUES (100, 'Inne');


--
-- Data for Name: product; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.product (product_id, category, name) VALUES (2, 1, 'Ziemniaki');
INSERT INTO public.product (product_id, category, name) VALUES (5, 1, 'Papryka czerwona');
INSERT INTO public.product (product_id, category, name) VALUES (9, 2, 'Winogrona jasne');
INSERT INTO public.product (product_id, category, name) VALUES (14, 3, 'Jogurt naturalny');
INSERT INTO public.product (product_id, category, name) VALUES (15, 4, 'Chleb pszenny');
INSERT INTO public.product (product_id, category, name) VALUES (16, 4, 'Chleb żytni');
INSERT INTO public.product (product_id, category, name) VALUES (17, 4, 'Bułka kajzerka');
INSERT INTO public.product (product_id, category, name) VALUES (18, 5, 'Czekolada mleczna');
INSERT INTO public.product (product_id, category, name) VALUES (19, 5, 'Ciastka owsiane');
INSERT INTO public.product (product_id, category, name) VALUES (20, 5, 'Żelki owocowe');
INSERT INTO public.product (product_id, category, name) VALUES (21, 6, 'Pierś z kurczaka');
INSERT INTO public.product (product_id, category, name) VALUES (24, 7, 'Woda mineralna niegazowana');
INSERT INTO public.product (product_id, category, name) VALUES (27, 8, 'Pizza mrożona');
INSERT INTO public.product (product_id, category, name) VALUES (28, 8, 'Mieszanka warzywna na patelnię');
INSERT INTO public.product (product_id, category, name) VALUES (29, 9, 'Makaron spaghetti');
INSERT INTO public.product (product_id, category, name) VALUES (31, 9, 'Kasza gryczana');
INSERT INTO public.product (product_id, category, name) VALUES (32, 9, 'Mąka pszenna');
INSERT INTO public.product (product_id, category, name) VALUES (33, 10, 'Chipsy paprykowe');
INSERT INTO public.product (product_id, category, name) VALUES (34, 10, 'Orzeszki ziemne solone');
INSERT INTO public.product (product_id, category, name) VALUES (35, 11, 'Kukurydza w puszce');
INSERT INTO public.product (product_id, category, name) VALUES (36, 11, 'Ketchup łagodny');
INSERT INTO public.product (product_id, category, name) VALUES (38, 12, 'Płyn do mycia naczyń');
INSERT INTO public.product (product_id, category, name) VALUES (39, 13, 'Żel pod prysznic');
INSERT INTO public.product (product_id, category, name) VALUES (40, 13, 'Pasta do zębów');
INSERT INTO public.product (product_id, category, name) VALUES (43, 5, 'Żelki');
INSERT INTO public.product (product_id, category, name) VALUES (44, 3, 'Majonez');
INSERT INTO public.product (product_id, category, name) VALUES (1, 1, 'Pomidory');
INSERT INTO public.product (product_id, category, name) VALUES (3, 1, 'Cebule');
INSERT INTO public.product (product_id, category, name) VALUES (4, 1, 'Marchewki');
INSERT INTO public.product (product_id, category, name) VALUES (6, 2, 'Banany');
INSERT INTO public.product (product_id, category, name) VALUES (7, 2, 'Jabłka');
INSERT INTO public.product (product_id, category, name) VALUES (8, 2, 'Cytryny');
INSERT INTO public.product (product_id, category, name) VALUES (11, 3, 'Jajka');
INSERT INTO public.product (product_id, category, name) VALUES (10, 3, 'Mleko');
INSERT INTO public.product (product_id, category, name) VALUES (12, 3, 'Masło');
INSERT INTO public.product (product_id, category, name) VALUES (13, 3, 'Ser żółty');
INSERT INTO public.product (product_id, category, name) VALUES (22, 6, 'Szynka');
INSERT INTO public.product (product_id, category, name) VALUES (23, 6, 'Kiełbasa');
INSERT INTO public.product (product_id, category, name) VALUES (25, 7, 'Sok jabłkowy');
INSERT INTO public.product (product_id, category, name) VALUES (26, 7, 'Coca-cola');
INSERT INTO public.product (product_id, category, name) VALUES (30, 9, 'Ryż biały');
INSERT INTO public.product (product_id, category, name) VALUES (37, 12, 'Papier toaletowy');
INSERT INTO public.product (product_id, category, name) VALUES (41, 2, 'Pomarańcze');
INSERT INTO public.product (product_id, category, name) VALUES (42, 1, 'Cukinie');
INSERT INTO public.product (product_id, category, name) VALUES (45, 3, 'Mozzarella');
INSERT INTO public.product (product_id, category, name) VALUES (46, 3, 'Ser pleśniowy');
INSERT INTO public.product (product_id, category, name) VALUES (47, 1, 'Papryka zielona');
INSERT INTO public.product (product_id, category, name) VALUES (48, 1, 'Ogórek zielony');
INSERT INTO public.product (product_id, category, name) VALUES (49, 1, 'Ogórki kwaszone');
INSERT INTO public.product (product_id, category, name) VALUES (50, 1, 'Papryka żółta');
INSERT INTO public.product (product_id, category, name) VALUES (51, 1, 'Kalafior');
INSERT INTO public.product (product_id, category, name) VALUES (56, 2, 'Ananas fresh ');
INSERT INTO public.product (product_id, category, name) VALUES (57, 2, 'Borówki amerykańskie ');
INSERT INTO public.product (product_id, category, name) VALUES (58, 1, 'Cebula czerwona ');
INSERT INTO public.product (product_id, category, name) VALUES (59, 12, 'Balsam po goleniu ');
INSERT INTO public.product (product_id, category, name) VALUES (55, 11, 'Tuńczyk puszka');
INSERT INTO public.product (product_id, category, name) VALUES (60, 4, 'Chleb żytni z żurawiną');
INSERT INTO public.product (product_id, category, name) VALUES (61, 4, 'Chleb tostowy maślany');
INSERT INTO public.product (product_id, category, name) VALUES (62, 11, 'Powidła śliwkowe');
INSERT INTO public.product (product_id, category, name) VALUES (63, 1, 'Burak świeży');


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.users (user_id, login, password) VALUES (1, 'michal', 'michal');
INSERT INTO public.users (user_id, login, password) VALUES (2, 'zosia', 'zosia');
INSERT INTO public.users (user_id, login, password) VALUES (3, 'wojtek', 'wojtek');
INSERT INTO public.users (user_id, login, password) VALUES (4, 'aga', 'aga');


--
-- PostgreSQL database dump complete
--

\unrestrict xqzqzbtcGodd4a8vDN6BfLoRfKPUrDfdy0IlwDUDeeidHhs8gvrQZMhPEycRiHm

