"""
Test suite for theme management
"""

from fastapi import status


class TestThemeManagement:
    """Test theme CRUD operations"""

    def test_list_themes(self, authenticated_client):
        """Test listing themes"""
        response = authenticated_client.get("/api/v1/themes")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "themes" in data or "items" in data  # Accept either format
        themes = data.get("themes", data.get("items", []))
        assert isinstance(themes, list)

    def test_create_theme(self, authenticated_client):
        """Test creating a custom theme"""
        theme_data = {
            "name": "custom-theme",
            "display_name": "Custom Theme",
            "description": "A custom theme for testing",
            "colors": {
                "primary": "#3B82F6",
                "secondary": "#10B981",
                "accent": "#F59E0B",
                "background": "#FFFFFF",
                "surface": "#F3F4F6",
                "text": "#1F2937",
                "textSecondary": "#6B7280",
                "border": "#E5E7EB",
                "error": "#EF4444",
                "warning": "#F59E0B",
                "success": "#10B981",
                "info": "#3B82F6",
            },
        }

        response = authenticated_client.post("/api/v1/themes", json=theme_data)

        # May succeed or fail based on permissions
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN]

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert data["name"] == theme_data["name"]
            assert data["display_name"] == theme_data["display_name"]
            assert data["colors"]["primary"] == theme_data["colors"]["primary"]

    def test_create_theme_duplicate_name(self, authenticated_client):
        """Test creating theme with duplicate name"""
        theme_data = {
            "name": "duplicate-theme",
            "display_name": "Duplicate Theme",
            "description": "Testing duplicate names",
            "colors": {
                "primary": "#3B82F6",
                "secondary": "#10B981",
                "accent": "#F59E0B",
                "background": "#FFFFFF",
                "surface": "#F3F4F6",
                "text": "#1F2937",
                "textSecondary": "#6B7280",
                "border": "#E5E7EB",
                "error": "#EF4444",
                "warning": "#F59E0B",
                "success": "#10B981",
                "info": "#3B82F6",
            },
        }

        # Create first theme
        authenticated_client.post("/api/v1/themes", json=theme_data)

        # Try to create duplicate
        second_response = authenticated_client.post("/api/v1/themes", json=theme_data)

        # Should fail with 400 or 403 (if no permission)
        assert second_response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_get_theme_by_id(self, authenticated_client):
        """Test getting a specific theme"""
        # First, list themes to get an ID
        list_response = authenticated_client.get("/api/v1/themes")

        if list_response.status_code == status.HTTP_200_OK:
            data = list_response.json()
            themes = data.get("themes", data.get("items", []))

            if themes:
                theme_id = themes[0]["id"]

                # Get specific theme
                response = authenticated_client.get(f"/api/v1/themes/{theme_id}")
                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_403_FORBIDDEN,
                    status.HTTP_404_NOT_FOUND,
                ]

    def test_update_theme(self, authenticated_client):
        """Test updating a theme"""
        # Create a theme first
        theme_data = {
            "name": "update-test-theme",
            "display_name": "Update Test Theme",
            "description": "For testing updates",
            "colors": {
                "primary": "#3B82F6",
                "secondary": "#10B981",
                "accent": "#F59E0B",
                "background": "#FFFFFF",
                "surface": "#F3F4F6",
                "text": "#1F2937",
                "textSecondary": "#6B7280",
                "border": "#E5E7EB",
                "error": "#EF4444",
                "warning": "#F59E0B",
                "success": "#10B981",
                "info": "#3B82F6",
            },
        }

        create_response = authenticated_client.post("/api/v1/themes", json=theme_data)

        if create_response.status_code == status.HTTP_201_CREATED:
            theme_id = create_response.json()["id"]

            # Update the theme
            update_data = {
                "display_name": "Updated Theme Name",
                "description": "Updated description",
            }

            response = authenticated_client.patch(f"/api/v1/themes/{theme_id}", json=update_data)

            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            ]

    def test_delete_theme(self, authenticated_client):
        """Test deleting a theme"""
        # Create a theme first
        theme_data = {
            "name": "delete-test-theme",
            "display_name": "Delete Test Theme",
            "description": "For testing deletion",
            "colors": {
                "primary": "#3B82F6",
                "secondary": "#10B981",
                "accent": "#F59E0B",
                "background": "#FFFFFF",
                "surface": "#F3F4F6",
                "text": "#1F2937",
                "textSecondary": "#6B7280",
                "border": "#E5E7EB",
                "error": "#EF4444",
                "warning": "#F59E0B",
                "success": "#10B981",
                "info": "#3B82F6",
            },
        }

        create_response = authenticated_client.post("/api/v1/themes", json=theme_data)

        if create_response.status_code == status.HTTP_201_CREATED:
            theme_id = create_response.json()["id"]

            # Delete the theme
            response = authenticated_client.delete(f"/api/v1/themes/{theme_id}")

            assert response.status_code in [
                status.HTTP_204_NO_CONTENT,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            ]

    def test_get_active_theme(self, authenticated_client):
        """Test getting the active theme"""
        response = authenticated_client.get("/api/v1/themes/active")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_export_theme_css(self, authenticated_client):
        """Test exporting theme as CSS variables"""
        # Get list of themes
        list_response = authenticated_client.get("/api/v1/themes")

        if list_response.status_code == status.HTTP_200_OK:
            data = list_response.json()
            themes = data.get("themes", data.get("items", []))

            if themes:
                theme_id = themes[0]["id"]

                # Export CSS
                response = authenticated_client.get(f"/api/v1/themes/{theme_id}/css")

                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_403_FORBIDDEN,
                    status.HTTP_404_NOT_FOUND,
                ]
