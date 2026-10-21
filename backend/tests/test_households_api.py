async def test_create_household(login_as):
    ala = await login_as("ala")

    response = await ala.post("/api/households", json={"name": "Dom"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Dom"
    assert [(m["login"], m["is_owner"]) for m in body["members"]] == [("ala", True)]


async def test_create_household_validates_name(login_as):
    ala = await login_as("ala")

    assert (await ala.post("/api/households", json={"name": ""})).status_code == 422
    assert (await ala.post("/api/households", json={"name": "x" * 101})).status_code == 422


async def test_member_cannot_create_another_household(household_with):
    (ala,) = await household_with("ala")

    assert (await ala.post("/api/households", json={"name": "Działka"})).status_code == 409


async def test_profile_with_household(household_with):
    (ala,) = await household_with("ala", name="Dom")

    household = (await ala.get("/api/users/me")).json()["household"]

    assert household["name"] == "Dom"
    assert isinstance(household["id"], int)


async def test_user_without_household_gets_409(login_as):
    ala = await login_as("ala")

    response = await ala.get("/api/households/me")

    assert response.status_code == 409
    assert "gospodarstwo" in response.json()["detail"]
    assert response.json()["code"] == "no_household"


async def test_removed_member_gets_no_household_code_on_list_and_chat(household_with):
    ala, ola = await household_with("ala", "ola")
    ola_id = (await ola.get("/api/users/me")).json()["id"]
    await ala.delete(f"/api/households/me/members/{ola_id}")

    list_response = await ola.get("/api/list")
    chat_response = await ola.post("/api/chat/messages", json={"content": "hej"})

    assert list_response.json()["code"] == chat_response.json()["code"] == "no_household"


async def test_other_conflicts_have_no_code(login_as):
    ala = await login_as("ala")
    await ala.post("/api/households", json={"name": "Dom"})

    response = await ala.post("/api/households", json={"name": "Drugi"})

    assert response.status_code == 409
    assert "code" not in response.json()


async def test_add_member_and_list_members(household_with):
    ala, ola = await household_with("ala", "ola")

    body = (await ola.get("/api/households/me")).json()

    assert [(m["login"], m["is_owner"]) for m in body["members"]] == [
        ("ala", True),
        ("ola", False),
    ]


async def test_add_unknown_login_returns_404(household_with):
    (ala,) = await household_with("ala")

    response = await ala.post("/api/households/me/members", json={"login": "nieznany"})

    assert response.status_code == 404


async def test_add_user_from_other_household_returns_409(household_with):
    (ala,) = await household_with("ala")
    await household_with("ola", name="Inny dom")

    response = await ala.post("/api/households/me/members", json={"login": "ola"})

    assert response.status_code == 409


async def test_regular_member_cannot_add_members(household_with, login_as):
    _, ola = await household_with("ala", "ola")
    await login_as("ewa")

    response = await ola.post("/api/households/me/members", json={"login": "ewa"})

    assert response.status_code == 403


async def test_owner_removes_member_who_loses_access(household_with):
    ala, ola = await household_with("ala", "ola")
    ola_id = (await ola.get("/api/users/me")).json()["id"]

    response = await ala.delete(f"/api/households/me/members/{ola_id}")

    assert response.status_code == 200
    assert (await ola.get("/api/households/me")).status_code == 409


async def test_owner_cannot_remove_self(household_with):
    (ala,) = await household_with("ala")
    ala_id = (await ala.get("/api/users/me")).json()["id"]

    response = await ala.delete(f"/api/households/me/members/{ala_id}")

    assert response.status_code == 403
    assert "opuszczenia" in response.json()["detail"]


async def test_member_leaves(household_with):
    ala, ola = await household_with("ala", "ola")

    assert (await ola.post("/api/households/me/leave")).status_code == 204

    assert (await ola.get("/api/users/me")).json()["household"] is None
    members = (await ala.get("/api/households/me")).json()["members"]
    assert [m["login"] for m in members] == ["ala"]


async def test_owner_leaves_and_ownership_passes(household_with):
    ala, ola, ewa = await household_with("ala", "ola", "ewa")

    await ala.post("/api/households/me/leave")

    members = (await ewa.get("/api/households/me")).json()["members"]
    assert [(m["login"], m["is_owner"]) for m in members] == [("ola", True), ("ewa", False)]


async def test_last_member_leaving_removes_household(household_with):
    (ala,) = await household_with("ala")

    await ala.post("/api/households/me/leave")

    assert (await ala.get("/api/households/me")).status_code == 409
    assert (await ala.post("/api/households", json={"name": "Nowy"})).status_code == 201
