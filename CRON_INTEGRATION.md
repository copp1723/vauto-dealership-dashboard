# Cron Management Integration Documentation

## Overview
This document describes the integration of the render-cron-api functionality into the vauto-dealership-dashboard as a super admin-only feature.

## Integration Components

### 1. Backend Components Added

#### Core Files
- `cron_routes.py` - FastAPI router with all cron management endpoints
- `auth_utils.py` - Shared authentication utilities for JWT validation
- `cron_services/` - Directory containing all cron-related services:
  - `config.py` - Configuration for Render API and Twilio
  - `cron_job_service.py` - Core cron job management service
  - `render_client.py` - Render API client
  - `dealership_service.py` - Dealership onboarding service
  - `dashboard_user_service.py` - User creation service
  - `twilio_phone_service.py` - Phone number management service
- `cron_models/` - Directory containing Pydantic models:
  - `cron_job.py` - All cron-related data models

### 2. Frontend Components

#### Templates
- `templates/cron_management.html` - Full-featured cron management UI page

#### UI Features
- Quick Onboard Dealership modal for streamlined onboarding
- Create Custom Cron Job modal for advanced configurations
- List of active cron jobs with management actions
- Super admin role verification on page load

### 3. API Endpoints

All endpoints are prefixed with `/api/cron/` and require super admin authentication:

- `POST /api/cron/jobs` - Create a new cron job
- `POST /api/cron/onboard` - Quick onboard a dealership (creates AM/PM jobs + user)
- `GET /api/cron/jobs` - List all cron jobs
- `GET /api/cron/jobs/{service_id}` - Get specific cron job details
- `PATCH /api/cron/jobs/{service_id}` - Update a cron job
- `DELETE /api/cron/jobs/{service_id}` - Delete a cron job
- `POST /api/cron/jobs/{service_id}/trigger` - Manually trigger a cron job
- `GET /api/cron/jobs/{service_id}/runs` - List runs for a cron job
- `DELETE /api/cron/jobs/{service_id}/runs/{run_id}` - Cancel a running job

## Configuration

### Required Environment Variables

Add these to your `.env` file:

```env
# Render API Configuration
RENDER_API_KEY=your-render-api-key-here
RENDER_API_BASE_URL=https://api.render.com/v1

# Twilio Configuration (Optional)
TWILIO_ACCOUNT_SID=your-twilio-sid-here
TWILIO_AUTH_TOKEN=your-twilio-token-here

# Default GitHub Repository
DEFAULT_GITHUB_REPO=https://github.com/your-org/dealership-automation
DEFAULT_GITHUB_BRANCH=main
```

### Getting API Keys

1. **Render API Key**:
   - Log into your Render account
   - Go to Account Settings > API Keys
   - Create a new API key with appropriate permissions

2. **Twilio Credentials** (Optional):
   - Log into Twilio Console
   - Find Account SID and Auth Token in the dashboard
   - Only needed if using automated phone number purchasing

## Usage

### Accessing Cron Management

1. Log in as a super admin user
2. Click on your user menu in the top right
3. Click "Cron Management" button (red button, only visible to super admins)
4. Or navigate directly to `/cron`

### Quick Onboarding a Dealership

1. Click "Quick Onboard Dealership" button
2. Fill in:
   - Dealership name
   - VAuto credentials
   - AM/PM job times
   - Dashboard user details
3. Click "Onboard Dealership"

This will automatically:
- Create AM and PM cron jobs
- Set up environment variables
- Create a dashboard user account
- Configure all necessary settings

### Creating Custom Cron Jobs

1. Click "Create Custom Cron Job" button
2. Configure:
   - Job name and schedule (cron expression)
   - GitHub repository URL and branch
   - Customer credentials
   - Phone number for 2FA
3. Click "Create Job"

### Managing Existing Jobs

For each cron job, you can:
- **Trigger** - Run the job immediately
- **View Runs** - See recent execution history
- **Delete** - Remove the job permanently

## Security

### Role-Based Access Control

- **Super Admin**: Full access to cron management features
- **Admin**: No access to cron management
- **User**: No access to cron management

The cron management page and all API endpoints verify super admin role before allowing access.

### Authentication Flow

1. JWT token from main dashboard authentication is reused
2. Each API call includes Bearer token in Authorization header
3. Backend verifies token and checks user role
4. Frontend checks user role on page load and shows/hides features

## Installation

1. Install required dependencies:
```bash
pip install httpx
```

2. Ensure all environment variables are set in `.env`

3. Restart the dashboard application:
```bash
python app.py
```

## Troubleshooting

### Common Issues

1. **"Super admin access required" error**
   - Ensure you're logged in with a super_admin role account
   - Check user role in the database

2. **Render API errors**
   - Verify RENDER_API_KEY is correct
   - Check Render API key permissions
   - Ensure Render account has available resources

3. **Cron Management button not visible**
   - Verify user role is super_admin
   - Check browser console for JavaScript errors
   - Clear browser cache and reload

### Debug Mode

To debug authentication issues:
1. Open browser console
2. Check `window.currentUser` to see logged-in user details
3. Verify `role` field is "super_admin"

## Future Enhancements

Potential improvements to consider:

1. **Logging**: Add detailed logging for all cron operations
2. **Audit Trail**: Track who created/modified/deleted cron jobs
3. **Job Monitoring**: Real-time status updates for running jobs
4. **Bulk Operations**: Ability to manage multiple jobs at once
5. **Template System**: Save and reuse common cron job configurations
6. **Notification System**: Alert on job failures or completions
7. **Resource Monitoring**: Track Render resource usage
8. **Backup/Restore**: Export and import cron job configurations

## Support

For issues or questions about the cron management integration:
1. Check this documentation
2. Review error messages in browser console
3. Check application logs for backend errors
4. Verify all environment variables are correctly set