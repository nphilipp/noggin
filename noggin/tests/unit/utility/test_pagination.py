import pytest
from bs4 import BeautifulSoup

from noggin import ipa_admin
from noggin.utility.pagination import PagedResult


@pytest.fixture
def many_dummy_groups(ipa_testing_config):
    all_fas_groups = ipa_admin.group_find(fasgroup=True)["result"]
    ipa_admin.batch(
        methods=[
            {"method": "group_del", "params": [[entry["cn"][0]], {}]}
            for entry in all_fas_groups
        ]
    )
    group_list = [f"dummy-group-{i:02d}" for i in range(1, 11)]
    ipa_admin.batch(
        methods=[
            {"method": "group_add", "params": [[name], {"fasgroup": True}]}
            for name in group_list
        ]
    )
    yield
    ipa_admin.batch(
        methods=[{"method": "group_del", "params": [[name], {}]} for name in group_list]
    )


@pytest.mark.vcr()
def test_groups_page(client, logged_in_dummy_user, many_dummy_groups):
    """Test the paginated groups list"""
    result = client.get("/groups/?page_number=2&page_size=3")
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    groups = page.select("ul.list-group li")
    group_names = [g.find("span", class_="title").get_text(strip=True) for g in groups]
    assert group_names == [
        "dummy-group-04",
        "dummy-group-05",
        "dummy-group-06",
    ]

    pagination_bar = page.select_one("ul.pagination")
    assert pagination_bar is not None
    # Prev
    prev_link = pagination_bar.select_one("li:first-child a.page-link")
    assert prev_link is not None
    assert prev_link["href"] == "/groups/?page_number=1&page_size=3"
    # Next
    next_link = pagination_bar.select_one("li:last-child a.page-link")
    assert next_link is not None
    assert next_link["href"] == "/groups/?page_number=3&page_size=3"
    # Other links
    assert len(pagination_bar.select("li.page-item")) == 6


@pytest.mark.vcr()
def test_groups_page_nopaging(client, logged_in_dummy_user, mocker):
    ipa = mocker.Mock(name="ipa")
    mocker.patch("noggin.utility.maybe_ipa_session", return_value=ipa)
    ipa.user_find.return_value = {"result": [{"uid": "dummy"}]}
    ipa.group_find.return_value = {"result": [{"cn": "dummy-1"}, {"cn": "dummy-2"}]}
    result = client.get("/groups/?page_size=0")
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    groups = page.select("ul.list-group li")
    assert len(groups) == 2
    ipa.group_find.assert_called_with(fasgroup=True, all=True)
    ipa.batch.assert_not_called()


def test_pagination_result_no_paging():
    result = PagedResult(items=["dummy"], page_size=0, page_number=1)
    assert result.total_pages == 1


def test_pagination_result():
    result = PagedResult(items=["dummy"], page_size=2, page_number=1)
    assert result.page_url(0) is None
    assert result.page_url(2) is None
    assert repr(result) == "<PagedResult items=[1 items] page=1>"
    assert result == PagedResult(items=["dummy"], page_size=2, page_number=1)
    with pytest.raises(ValueError):
        result == object()
