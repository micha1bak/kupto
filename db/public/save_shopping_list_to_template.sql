create procedure save_shopping_list_to_template(IN _template_id integer)
    language plpgsql
as
$$
BEGIN
    INSERT INTO template_item (template_id, product_id, quantity)
    SELECT _template_id, product_id, quantity
    FROM Shopping_list;
END;
$$;

alter procedure save_shopping_list_to_template(integer) owner to postgres;

