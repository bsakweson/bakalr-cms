# Permissions Matrix

This document outlines all permissions and their assignments across roles in Bakalr CMS.

## Role Permission Summary

| Role | Permissions | Description |
|------|-------------|-------------|
| **owner** | 117 (all) | Organization owner with full access |
| **admin** | 113 | Full administrative access except owner management |
| **manager** | 41 | Store/business management |
| **sales** | 15 | Sales and POS operations |
| **inventory_manager** | 13 | Inventory and stock management |
| **editor** | 11 | Content editing and publishing |
| **employee** | 10 | Basic employee access |
| **contributor** | 5 | Content creation without publishing |
| **api_consumer** | 3 | External API access |
| **viewer** | 3 | Read-only access |

## Owner-Only Permissions

These permissions are restricted to the **owner** role only:

| Permission | Description |
|------------|-------------|
| `organization.delete` | Delete the organization |
| `organization.settings.manage` | Manage organization settings |
| `system.admin` | System-level admin access |
| `user.manage.full` | Full user management (including owner) |

## Full Permissions Matrix

| Permission            | Category      | owner | admin | manager | sales | inventory_manager | editor | employee | contributor | api_consumer | viewer |
|-----------------------|---------------|:-----:|:-----:|:-------:|:-----:|:-----------------:|:------:|:--------:|:-----------:|:------------:|:------:|
| admin.metrics         | admin         |   ✓   |   ✓   |         |       |                   |        |          |             |              |        |
| analytics.export      | analytics     |   ✓   |   ✓   |    ✓    |       |                   |        |          |             |              |        |
| analytics.view        | analytics     |   ✓   |   ✓   |    ✓    |   ✓   |         ✓         |        |          |             |              |        |
| audit.logs            | audit         |   ✓   |   ✓   |    ✓    |       |                   |        |          |             |              |        |
| audit.view            | audit         |   ✓   |   ✓   |         |       |                   |        |          |             |              |        |
| categories.create     | categories    |   ✓   |   ✓   |         |       |                   |        |          |             |              |        |
| categories.delete     | categories    |   ✓   |   ✓   |         |       |                   |        |          |             |              |        |
| categories.manage     | categories    |   ✓   |   ✓   |         |       |                   |        |          |             |              |        |
| categories.read       | categories    |   ✓   |   ✓   |         |       |                   |        |          |             |              |        |
| categories.update     | categories    |   ✓   |   ✓   |         |       |                   |        |          |             |              |        |
| content.create        | content       |   ✓   |   ✓   |    ✓    |       |         ✓         |   ✓    |          |      ✓      |              |        |
| content.delete        | content       |   ✓   |   ✓   |         |       |                   |   ✓    |          |             |              |        |
| content.manage        | content       |   ✓   |   ✓   |         |       |                   |        |          |             |              |        |
| content.publish       | content       |   ✓   |   ✓   |    ✓    |       |         ✓         |   ✓    |          |             |              |        |
| content.read          | content       |   ✓   |   ✓   |    ✓    |   ✓   |         ✓         |   ✓    |    ✓     |      ✓      |      ✓       |   ✓    |
| content.unpublish     | content       |   ✓   |   ✓   |    ✓    |       |                   |        |          |             |              |        |
| content.update        | content       |   ✓   |   ✓   |    ✓    |       |         ✓         |   ✓    |          |      ✓      |              |        |
| content.type.create   | content_type  |   ✓   |   ✓   |         |       |                   |        |          |             |              |        |
| content.type.delete   | content_type  |   ✓   |   ✓   |         |       |                   |        |          |             |              |        |
| content.type.read     | content_type  |   ✓   |   ✓   |    ✓    |   ✓   |         ✓         |        |    ✓     |             |              |        |
| content.type.update   | content_type  |   ✓   |   ✓   |         |       |                   |        |          |             |              |        |
| customers.create | customers | ✓ | ✓ |  |  |  |  |  |  |  |  |
| customers.delete | customers | ✓ | ✓ |  |  |  |  |  |  |  |  |
| customers.manage | customers | ✓ | ✓ |  |  |  |  |  |  |  |  |
| customers.read | customers | ✓ | ✓ |  |  |  |  |  |  |  |  |
| customers.update | customers | ✓ | ✓ |  |  |  |  |  |  |  |  |
| employees.create | employees | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| employees.delete | employees | ✓ | ✓ |  |  |  |  |  |  |  |  |
| employees.manage | employees | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| employees.read | employees | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| employees.schedule | employees | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| employees.self.read | employees | ✓ | ✓ |  | ✓ |  |  | ✓ |  |  |  |
| employees.self.update | employees | ✓ | ✓ |  | ✓ |  |  | ✓ |  |  |  |
| employees.stats | employees | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| employees.update | employees | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| inventory.create | inventory | ✓ | ✓ |  |  |  |  |  |  |  |  |
| inventory.delete | inventory | ✓ | ✓ |  |  |  |  |  |  |  |  |
| inventory.manage | inventory | ✓ | ✓ |  |  |  |  |  |  |  |  |
| inventory.read | inventory | ✓ | ✓ |  |  |  |  |  |  |  |  |
| inventory.reports | inventory | ✓ | ✓ |  |  |  |  |  |  |  |  |
| inventory.stock.adjust | inventory | ✓ | ✓ |  |  |  |  |  |  |  |  |
| inventory.stock.transfer | inventory | ✓ | ✓ |  |  |  |  |  |  |  |  |
| inventory.update | inventory | ✓ | ✓ |  |  |  |  |  |  |  |  |
| locale.create | locale | ✓ | ✓ |  |  |  |  |  |  |  |  |
| locale.delete | locale | ✓ | ✓ |  |  |  |  |  |  |  |  |
| locale.read | locale | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  |  |  |
| locale.update | locale | ✓ | ✓ |  |  |  |  |  |  |  |  |
| media.delete | media | ✓ | ✓ |  |  |  | ✓ |  |  |  |  |
| media.read | media | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| media.update | media | ✓ | ✓ | ✓ |  | ✓ | ✓ |  |  |  |  |
| media.upload | media | ✓ | ✓ | ✓ |  | ✓ |  |  |  |  |  |
| notification.create | notification | ✓ | ✓ |  |  |  |  |  |  |  |  |
| notification.delete | notification | ✓ | ✓ |  |  |  |  |  |  |  |  |
| notification.read | notification | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  |  |  |
| notification.view | notification | ✓ | ✓ |  |  |  |  |  |  |  |  |
| orders.cancel | orders | ✓ | ✓ |  |  |  |  |  |  |  |  |
| orders.create | orders | ✓ | ✓ |  |  |  |  |  |  |  |  |
| orders.manage | orders | ✓ | ✓ |  |  |  |  |  |  |  |  |
| orders.read | orders | ✓ | ✓ |  |  |  |  |  |  |  |  |
| orders.refund | orders | ✓ | ✓ |  |  |  |  |  |  |  |  |
| orders.update | orders | ✓ | ✓ |  |  |  |  |  |  |  |  |
| **organization.delete** | organization | ✓ |  |  |  |  |  |  |  |  |  |
| organization.read | organization | ✓ | ✓ |  |  |  |  |  |  |  |  |
| **organization.settings.manage** | organization | ✓ |  |  |  |  |  |  |  |  |  |
| organization.settings.view | organization | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| organization.update | organization | ✓ | ✓ |  |  |  |  |  |  |  |  |
| permission.manage | permission | ✓ | ✓ |  |  |  |  |  |  |  |  |
| permission.read | permission | ✓ | ✓ |  |  |  |  |  |  |  |  |
| pos.access | pos | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  |  |  |
| pos.cash.drawer | pos | ✓ | ✓ | ✓ | ✓ |  |  |  |  |  |  |
| pos.discount | pos | ✓ | ✓ | ✓ | ✓ |  |  |  |  |  |  |
| pos.discount.manager | pos | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| pos.end.shift | pos | ✓ | ✓ | ✓ | ✓ |  |  |  |  |  |  |
| pos.manage | pos | ✓ | ✓ |  |  |  |  |  |  |  |  |
| pos.refund | pos | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| pos.reports | pos | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| pos.sell | pos | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  |  |  |
| pos.void | pos | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| products.create | products | ✓ | ✓ |  |  |  |  |  |  |  |  |
| products.delete | products | ✓ | ✓ |  |  |  |  |  |  |  |  |
| products.manage | products | ✓ | ✓ |  |  |  |  |  |  |  |  |
| products.pricing | products | ✓ | ✓ |  |  |  |  |  |  |  |  |
| products.read | products | ✓ | ✓ |  |  |  |  |  |  |  |  |
| products.update | products | ✓ | ✓ |  |  |  |  |  |  |  |  |
| reference_data.create | reference_data | ✓ | ✓ |  |  |  |  |  |  |  |  |
| reference_data.delete | reference_data | ✓ | ✓ |  |  |  |  |  |  |  |  |
| reference_data.read | reference_data | ✓ | ✓ | ✓ |  |  |  |  |  | ✓ |  |
| reference_data.update | reference_data | ✓ | ✓ |  |  |  |  |  |  |  |  |
| role.create | role | ✓ | ✓ |  |  |  |  |  |  |  |  |
| role.delete | role | ✓ | ✓ |  |  |  |  |  |  |  |  |
| role.manage | role | ✓ | ✓ |  |  |  |  |  |  |  |  |
| role.read | role | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| role.update | role | ✓ | ✓ |  |  |  |  |  |  |  |  |
| role.view | role | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| seo.read | seo | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| seo.update | seo | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| **system.admin** | system | ✓ |  |  |  |  |  |  |  |  |  |
| system.settings | system | ✓ | ✓ |  |  |  |  |  |  |  |  |
| template.create | template | ✓ | ✓ |  |  |  |  |  |  |  |  |
| template.delete | template | ✓ | ✓ |  |  |  |  |  |  |  |  |
| template.read | template | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  |  |
| template.update | template | ✓ | ✓ |  |  |  |  |  |  |  |  |
| theme.create | theme | ✓ | ✓ |  |  |  |  |  |  |  |  |
| theme.delete | theme | ✓ | ✓ |  |  |  |  |  |  |  |  |
| theme.manage | theme | ✓ | ✓ |  |  |  |  |  |  |  |  |
| theme.read | theme | ✓ | ✓ |  |  |  |  |  |  |  |  |
| theme.update | theme | ✓ | ✓ |  |  |  |  |  |  |  |  |
| translation.create | translation | ✓ | ✓ | ✓ |  |  | ✓ |  |  |  |  |
| translation.delete | translation | ✓ | ✓ |  |  |  |  |  |  |  |  |
| translation.read | translation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| translation.update | translation | ✓ | ✓ | ✓ |  |  | ✓ |  |  |  |  |
| user.create | user | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| user.delete | user | ✓ | ✓ |  |  |  |  |  |  |  |  |
| user.manage | user | ✓ | ✓ |  |  |  |  |  |  |  |  |
| **user.manage.full** | user | ✓ |  |  |  |  |  |  |  |  |  |
| user.read | user | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| user.update | user | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| webhook.create | webhook | ✓ | ✓ |  |  |  |  |  |  |  |  |
| webhook.delete | webhook | ✓ | ✓ |  |  |  |  |  |  |  |  |
| webhook.read | webhook | ✓ | ✓ |  |  |  |  |  |  |  |  |
| webhook.update | webhook | ✓ | ✓ |  |  |  |  |  |  |  |  |

> **Note:** Permissions in **bold** are owner-only and cannot be assigned to admin or other roles.

## Permission Categories

| Category | Count | Description |
|----------|-------|-------------|
| `admin` | 1 | Administrative metrics and monitoring |
| `analytics` | 2 | Analytics viewing and export |
| `audit` | 2 | Audit log access |
| `categories` | 5 | Category management |
| `content` | 7 | Content entry management |
| `content_type` | 4 | Content type schema management |
| `customers` | 5 | Customer management |
| `employees` | 9 | Employee management |
| `inventory` | 8 | Inventory and stock management |
| `locale` | 4 | Locale/language management |
| `media` | 4 | Media file management |
| `notification` | 4 | Notification management |
| `orders` | 6 | Order management |
| `organization` | 5 | Organization settings |
| `permission` | 2 | Permission management |
| `pos` | 10 | Point of Sale operations |
| `products` | 6 | Product catalog management |
| `reference_data` | 4 | Reference data management (departments, roles, statuses) |
| `role` | 6 | Role management |
| `seo` | 2 | SEO metadata management |
| `system` | 2 | System-level settings |
| `template` | 4 | Content template management |
| `theme` | 5 | Theme management |
| `translation` | 4 | Translation management |
| `user` | 6 | User management |
| `webhook` | 4 | Webhook management |

**Total: 121 permissions across 26 categories**

---

*Last updated: December 22, 2025*
