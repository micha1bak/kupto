create function validate_user(_login character varying, _password character varying) returns text
    language plpgsql
as
$$
DECLARE
	is_valid int;
BEGIN
	select u.user_id 
	from users u
	where u.login = _login and u.password = _password
	into is_valid;
	return coalesce(is_valid, 0);
END; $$;

alter function validate_user(varchar, varchar) owner to postgres;

