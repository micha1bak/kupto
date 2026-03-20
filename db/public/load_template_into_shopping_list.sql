create procedure load_template_into_shopping_list(IN _template_id integer)
    language plpgsql
as
$$
DECLARE
v_user_id INT;
BEGIN

	select user_id 
	from template
	where template_id = _template_id
	into v_user_id;
	
    INSERT INTO shopping_list (product_id, added_by_user_id, quantity)
    SELECT product_id, v_user_id , quantity
    FROM template_item
	WHERE template_id = _template_id
	ON CONFLICT (product_id) DO NOTHING; 	
END;
$$;

alter procedure load_template_into_shopping_list(integer) owner to postgres;

