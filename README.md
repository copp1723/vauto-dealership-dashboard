# Dealership Dashboard

A professional web-based dashboard built with **FastAPI** for monitoring and analyzing vehicle processing activities. This modern dashboard provides real-time insights into vehicle processing status, feature marking, description updates, and NO FEAR certifications with automatic API documentation and type safety.

## Features

### 📊 **Real-time Statistics**
- Total vehicles processed
- Processing success rate
- Descriptions updated count
- Features marked statistics
- NO FEAR certificates issued
- Recent activity tracking (7 days)

### 🔍 **Advanced Search & Filtering**
- Search vehicles by stock number
- Filter by processing status (successful/failed)
- Filter by description update status
- Real-time search with debouncing
- Keyboard shortcuts (press `/` to focus search)

### 🚗 **Vehicle Management**
- Professional vehicle cards with key information
- Detailed vehicle information modals
- Processing duration tracking
- Feature marking counts
- Description preview
- VIN and odometer display
- Days in inventory tracking

### 📱 **User-Friendly Interface**
- Responsive design for desktop, tablet, and mobile
- Professional gradient design
- Intuitive navigation
- Toast notifications
- Loading states and error handling
- Pagination for large datasets

### 📈 **Activity Monitoring**
- Recent processing activity feed
- Time-based activity tracking
- Success/failure indicators
- Quick access to vehicle details

### 🚀 **Modern FastAPI Backend**
- Automatic interactive API documentation
- Type-safe API responses with Pydantic models  
- High performance async/await support
- Built-in request validation and serialization
- OpenAPI/Swagger UI at `/api/docs`
- ReDoc documentation at `/api/redoc`

## Installation

### Prerequisites
- Python 3.7 or higher
- Vehicle processing database (created by the main automation system)

### Quick Start
1. Navigate to the dashboard directory:
   ```bash
   cd dealership_dashboard
   ```

2. Run the startup script:
   ```bash
   python run_dashboard.py
   ```

3. Open your browser and visit:
   ```
   http://localhost:8000
   ```

4. Explore the automatic API documentation:
   ```
   http://localhost:8000/api/docs      (Interactive Swagger UI)
   http://localhost:8000/api/redoc     (ReDoc documentation)
   ```

### Manual Installation
If you prefer to install manually:

```bash
# Install requirements
pip install -r requirements.txt

# Start the dashboard
python app.py
```

## Usage

### Dashboard Overview
The dashboard displays six main statistics cards:
- **Total Vehicles**: Number of vehicles processed
- **Success Rate**: Percentage of successful processing
- **Descriptions Updated**: Count of vehicles with updated descriptions
- **Features Marked**: Total features marked across all vehicles
- **NO FEAR Certificates**: Number of certified vehicles
- **Recent Activity**: Activity in the last 7 days

### Searching Vehicles
- Use the search box to find vehicles by stock number
- Apply filters for processing status or description updates
- Results update automatically as you type
- Use the clear button (×) to reset search

### Vehicle Details
- Click on any vehicle card to view detailed information
- Modal window displays complete processing information
- Shows starred features, descriptions, certifications, and errors
- Close modal with the X button or press Escape key

### Recent Activity
- Monitor the latest processing activities
- Click on activity items to view vehicle details
- Activities are sorted by most recent first

## Technical Details

### Architecture
- **Backend**: FastAPI with async/await support and SQLAlchemy ORM
- **Frontend**: Modern HTML5, CSS3, and JavaScript
- **Database**: SQLite with the vehicle processing schema
- **API Documentation**: Automatic OpenAPI/Swagger generation
- **Data Validation**: Pydantic models for type safety
- **Styling**: Professional gradient design with responsive layout
- **Icons**: Font Awesome icons for visual consistency

### API Endpoints
All endpoints include automatic documentation and validation:

- `GET /api/vehicles` - Paginated vehicle list with search (supports query parameters)
- `GET /api/vehicle/{vehicle_id}` - Detailed vehicle information  
- `GET /api/statistics` - Dashboard statistics
- `GET /api/recent-activity` - Recent processing activity (configurable limit)
- `GET /health` - Health check endpoint
- `GET /api/docs` - Interactive API documentation (Swagger UI)
- `GET /api/redoc` - Alternative API documentation (ReDoc)

### Pydantic Models
Type-safe data structures ensure API reliability:
- `VehicleInfo` - Basic vehicle information for listings
- `VehicleDetail` - Complete vehicle details with all processing data
- `Statistics` - Dashboard statistics structure
- `ActivityItem` - Recent activity item structure
- `PaginationInfo` - Pagination metadata

### Data Sources
The dashboard reads from the `vehicle_processing.db` database created by the main automation system. It displays:
- Vehicle basic information (stock number, VIN, odometer)
- Processing results and timing
- Feature marking decisions
- Description updates
- NO FEAR certifications
- Error logs and diagnostics

## Customization

### Styling
- Modify `static/css/dashboard.css` to customize the appearance
- The design uses CSS custom properties for easy color scheme changes
- Responsive breakpoints are defined for mobile compatibility

### Functionality
- Add new API endpoints in `app.py`
- Extend the JavaScript dashboard class in `static/js/dashboard.js`
- Update the HTML template in `templates/dashboard.html`

## Browser Compatibility
- Chrome 70+
- Firefox 65+
- Safari 12+
- Edge 79+

## Performance
- Pagination prevents loading large datasets
- Debounced search reduces API calls
- Responsive design optimizes mobile performance
- Efficient database queries with indexes

## Security
- Input sanitization prevents XSS attacks
- SQL injection protection via SQLAlchemy ORM
- CORS configured for development use
- No sensitive data exposure in client-side code

## Troubleshooting

### Common Issues

**Dashboard won't start:**
- Ensure Python 3.7+ is installed
- Run `pip install -r requirements.txt`
- Check that port 8000 is not in use
- Verify FastAPI and Uvicorn are properly installed

**No data displayed:**
- Verify the vehicle processing database exists
- Ensure the database path is correct in the parent directory
- Run the main automation system to create sample data

**Search not working:**
- Check browser console for JavaScript errors
- Ensure network connectivity to the FastAPI server
- Verify API endpoints are responding at `/api/docs`
- Test individual endpoints using the interactive documentation

**Mobile display issues:**
- Clear browser cache
- Check viewport meta tag
- Verify CSS media queries are working

### Support
For technical support or questions about the dashboard:
1. Check the browser console for error messages
2. Verify all dependencies are installed
3. Ensure the database is accessible and contains data
4. Check that the FastAPI server is running without errors
5. Use the interactive API documentation at `/api/docs` to test endpoints
6. Check the server logs for detailed error information

## Future Enhancements
- Export functionality for reports
- Advanced filtering options
- Date range selection
- Bulk operations
- Dashboard customization settings
- Real-time updates via WebSocket
- Integration with dealer management systems
- Database connection pooling for better performance
- Async database operations for higher concurrency
- Background tasks for report generation
- Authentication and authorization system