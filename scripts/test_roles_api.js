#!/usr/bin/env node
/**
 * Test script to verify roles API from frontend perspective
 */

const axios = require('axios');

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function testRolesAPI() {
  try {
    console.log('🔐 Logging in...');
    const loginResponse = await axios.post(`${API_BASE_URL}/api/v1/auth/login`, {
      email: 'bsakweson@gmail.com',
      password: 'Angelbenise123!@#',
    });

    const token = loginResponse.data.access_token;
    console.log('✅ Login successful');
    console.log('Token:', token.substring(0, 50) + '...');

    console.log('\n📋 Fetching roles...');
    const rolesResponse = await axios.get(`${API_BASE_URL}/api/v1/roles/`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    console.log('✅ Roles fetched successfully');
    console.log('Total:', rolesResponse.data.total);
    console.log('\nRoles:');
    rolesResponse.data.roles.forEach((role) => {
      console.log(`  - ${role.name} (ID: ${role.id})`);
      console.log(`    Permissions: ${role.permissions.length}`);
      console.log(`    Users: ${role.user_count}`);
    });

    console.log('\n🔐 Fetching permissions...');
    const permsResponse = await axios.get(`${API_BASE_URL}/api/v1/roles/permissions`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    console.log('✅ Permissions fetched successfully');
    console.log('Total:', permsResponse.data.total);

  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
  }
}

testRolesAPI();
