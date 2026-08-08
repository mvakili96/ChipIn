from uuid import uuid4

from playwright.sync_api import Page, expect


def test_admin_core_expense_flow(page: Page, app_url: str):
    suffix = uuid4().hex[:8]
    alice = f"E2E Alice {suffix}"
    bob = f"E2E Bob {suffix}"
    group_name = f"E2E Group {suffix}"
    expense_name = f"E2E Dinner {suffix}"

    page.goto(f"{app_url}/admin/")
    expect(page.locator("#api-status")).to_have_text("API online")

    _create_user(page, alice, f"alice-{suffix}@example.com")
    _create_user(page, bob, f"bob-{suffix}@example.com")

    page.locator("#group-name").fill(group_name)
    page.locator("#group-users label", has_text=alice).locator("input").check()
    page.locator("#group-users label", has_text=bob).locator("input").check()
    page.locator("#group-form button[type='submit']").click()

    expect(page.locator("#toast")).to_have_text("Group created")
    page.get_by_role("tab", name="Groups").click()
    expect(page.get_by_role("button", name=f"Open {group_name}")).to_be_visible()

    page.locator("#expense-name").fill(expense_name)
    page.locator("#expense-amount").fill("30")
    page.locator("#expense-group").select_option(label=group_name)
    page.locator("#expense-payer").select_option(label=alice)
    page.locator("#expense-form button[type='submit']").click()

    expect(page.locator("#toast")).to_have_text("Expense added")

    page.get_by_role("tab", name="Expenses").click()
    expense_row = page.locator("#expenses-table tr", has_text=expense_name)
    expect(expense_row).to_contain_text(group_name)
    expect(expense_row).to_contain_text(alice)
    expect(expense_row).to_contain_text("$30.00")

    page.get_by_role("tab", name="Settlements").click()
    settlement = page.locator("#settlements-list .settlement-item")
    expect(settlement).to_contain_text(f"{bob} pays {alice}")
    expect(settlement).to_contain_text("$15.00")

    page.get_by_role("tab", name="Expenses").click()
    expense_row.get_by_role("button", name=f"Delete {expense_name}").click()
    expect(page.locator("#toast")).to_have_text("Expense deleted")
    expect(page.locator("#expenses-table tr", has_text=expense_name)).to_have_count(0)

    page.get_by_role("tab", name="Groups").click()
    page.get_by_role("button", name=f"Delete {group_name}").click()
    expect(page.locator("#toast")).to_have_text("Group deleted")
    expect(page.get_by_role("button", name=f"Open {group_name}")).to_have_count(0)


def _create_user(page: Page, name: str, email: str):
    page.locator("#user-name").fill(name)
    page.locator("#user-email").fill(email)
    page.locator("#user-form button[type='submit']").click()

    expect(page.locator("#toast")).to_have_text("User added")
    expect(page.locator("#users-table tr", has_text=name)).to_contain_text(email)
