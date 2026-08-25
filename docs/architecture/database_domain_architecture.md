# Trazio Database and Domain Architecture

## Overview

This document describes the database and domain architecture for Phase 1B of the Trazio platform.

## Architecture Decision

- **Pattern**: API-first modular monolith
- **ORM**: SQLAlchemy 2.x with typed Python (Mapped type hints)
- **Database**: PostgreSQL with PostGIS extension
- **Migrations**: Alembic
- **Redis**: Exists in infrastructure but NOT used in Phase 1B business logic

## Entity Relationship Overview

### Core Entities

```
┌─────────────────┐
│      User       │
├─────────────────┤
│ id (PK)         │
│ email (UQ)      │
│ username (UQ)   │
│ hashed_password │
│ full_name       │
│ status          │
│ is_verified     │
│ created_at      │
│ updated_at      │
└────────┬────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐       ┌─────────────────┐
│    Session      │       │      Trip       │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ user_id (FK)    │       │ user_id (FK)    │
│ session_token   │       │ title           │
│ expires_at      │       │ description     │
│ status          │       │ start_location  │
│ ip_address      │       │ start_date      │
│ user_agent      │       │ start_time      │
│ device_info     │       │ end_date        │
└─────────────────┘       │ end_time        │
                        │ available_duration│
                        │ budget_level     │
                        │ budget_amount    │
                        │ budget_currency  │
                        │ transport_mode   │
                        │ preferences (JSON)│
                        │ status          │
                        │ is_public       │
                        │ share_token     │
                        └────────┬────────┘
                                 │
                                 │ 1:N
                                 ▼
                        ┌─────────────────┐
                        │   Itinerary     │
                        ├─────────────────┤
                        │ id (PK)         │
                        │ trip_id (FK)    │
                        │ version         │
                        │ status          │
                        │ notes           │
                        │ total_duration  │
                        │ estimated_travel│
                        │ estimated_cost  │
                        │ is_optimized    │
                        └────────┬────────┘
                                 │
                                 │ 1:N
                                 ▼
                        ┌─────────────────┐
                        │ ItineraryStop   │
                        ├─────────────────┤
                        │ id (PK)         │
                        │ itinerary_id(FK)│
                        │ destination_id  │
                        │ sequence        │
                        │ planned_arrival │
                        │ planned_depart  │
                        │ visit_duration  │
                        │ travel_duration │
                        │ travel_distance │
                        │ travel_mode     │
                        │ selection_reason│
                        │ notes           │
                        └─────────────────┘
```

```
┌─────────────────┐
│   Destination   │
├─────────────────┤
│ id (PK)         │
│ name            │
│ slug (UQ)       │
│ description     │
│ category        │
│ location (PT)   │ ← PostGIS POINT(srid=4326)
│ address fields  │
│ opening_hours   │
│ entry_fee       │
│ avg_visit_duration│
│ accessibility   │
│ popularity_score│
│ is_active       │
│ created_at      │
│ updated_at      │
└────────┬────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐
│ DestinationSource│
├─────────────────┤
│ id (PK)         │
│ destination_id  │
│ source_name     │
│ source_type     │
│ source_reference │
│ source_url      │
│ verification_status│
│ last_verified_at│
│ trust_score     │
│ notes           │
└─────────────────┘
```

```
┌─────────────────┐
│    Feedback     │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │
│ destination_id  │ (optional)
│ trip_id         │ (optional)
│ feedback_type   │
│ title           │
│ content         │
│ rating          │
│ is_anonymous    │
│ is_public       │
└─────────────────┘
```

## Entity Responsibilities

### User
- **Purpose**: Represent a registered user of the Trazio platform
- **Responsibilities**:
  - Authenticate and authorize actions (future: via Session)
  - Own trips and associated data
  - Store profile information
- **Constraints**:
  - Email must be unique
  - Username must be unique
  - Status defaults to ACTIVE

### Session
- **Purpose**: Server-side session tracking for persistent login
- **Responsibilities**:
  - Track authenticated user sessions
  - Store session metadata WITHOUT raw authentication secrets
  - Support secure session invalidation
- **Constraints**:
  - Session token must be unique
  - User ID is required
  - Expiration is required
- **Architecture Note**: Supports planned persistent-login architecture but does NOT implement authentication logic

### Destination
- **Purpose**: Tourism location/point of interest
- **Responsibilities**:
  - Store geographic and descriptive information
  - Support geospatial queries via PostGIS
  - Track popularity and accessibility
  - Provide foundation for itinerary planning
- **Constraints**:
  - Name is required
  - Slug must be unique
  - Location (PostGIS geometry) is required
  - Category is required
  - Active status defaults to True
- **PostGIS**: Uses GEOMETRY type with POINT geometry and SRID 4326 (WGS84)

### DestinationSource
- **Purpose**: Track provenance of destination information
- **Responsibilities**:
  - Record where destination data originated
  - Track verification status
  - Support data attribution and trust scoring
- **Constraints**:
  - Destination ID is required
  - Source name is required
- **Architecture Decision**: Enables knowing where important destination information came from

### Trip
- **Purpose**: User's travel planning requirements
- **Responsibilities**:
  - Store user's trip planning parameters
  - Track trip status through its lifecycle
  - Provide foundation for itinerary generation
  - Maintain extensibility for future requirements
- **Constraints**:
  - User ID is required
  - Title is required
  - Start date/location are required
  - Status defaults to DRAFT
- **Extensibility**: Preferences stored as JSON for flexibility

### Itinerary
- **Purpose**: Versioned travel plan for a trip
- **Responsibilities**:
  - Store ordered stops for a trip
  - Support versioning for dynamic replanning
  - Track duration and cost estimates
- **Constraints**:
  - Trip ID is required
  - Version is required and UNIQUE per trip
  - Status defaults to DRAFT
- **Versioning Strategy**:
  - Each trip can have multiple itinerary versions
  - Version number is monotonically increasing
  - Lower versions kept for history/audit
  - Latest version is typically the active one

### ItineraryStop
- **Purpose**: Ordered destination in an itinerary
- **Responsibilities**:
  - Store sequence/order of stops
  - Track planned timing for each stop
  - Store travel estimates between stops
  - Link to destination with additional context
- **Constraints**:
  - Itinerary ID is required
  - Destination ID is required
  - Sequence is required

### Feedback
- **Purpose**: User feedback associated with destinations or trips
- **Responsibilities**:
  - Store user ratings and reviews
  - Track feedback for destinations and trips
  - Support minimal extensibility
- **Constraints**:
  - User ID is required
  - Type is required
  - Either destination_id OR trip_id must be provided

## Important Constraints

### Check Constraints
- `popularity_score` between 0 and 100
- `trust_score` between 0 and 100
- `visit_duration` must be positive if not null
- `budget_amount` must be non-negative if not null
- `available_duration` must be positive if not null
- Trip `end_date` must be >= `start_date` if both provided

### Unique Constraints
- User: email, username
- Session: session_token
- Destination: slug
- Itinerary: (trip_id, version) composite unique
- Trip: share_token (nullable, unique)

### Foreign Key Constraints
All FK relationships use CASCADE delete where appropriate:
- User → Sessions, Trips, Feedbacks
- Trip → Itineraries, Feedbacks
- Destination → DestinationSources, ItineraryStops, Feedbacks
- Itinerary → ItineraryStops

## PostGIS Decision

### Why PostGIS?
- Native spatial data support in PostgreSQL
- Efficient geospatial queries (nearest neighbor, distance, containment)
- Industry standard for geographic applications
- Full indexing support (GiST indexes)

### Implementation
- Destination.location: GEOMETRY(POINT, srid=4326)
- Spatial index: `idx_destinations_location` using GIST
- SRID 4326: WGS84 coordinate system (lat/lon)

### Future Queries Supported
- Destinations within radius of a point
- Destinations near a route (linestring)
- Nearest N destinations to a point
- Bounding box queries

### Note
Route generation and actual geospatial queries are NOT implemented in Phase 1B. The schema supports them.

## Itinerary Versioning Decision

### Why Versioning?
- Dynamic replanning will create new itinerary versions
- Preserve history for audit and rollback
- Support A/B testing of itineraries
- User can compare different versions

### Implementation
- Version is an integer, monotonically increasing
- Each trip has one or more itineraries
- Unique constraint: (trip_id, version)
- Latest version is determined by highest version number per trip

## Source/Provenance Decision

### Why Track Source?
- Data comes from multiple providers
- Need to track trust/quality
- Legal/compliance requirements
- User attribution

### Implementation
- DestinationSource table links to Destination
- Fields: source_name, source_type, source_reference, source_url
- Verification: status, last_verified_at, trust_score
- Multiple sources can reference the same destination

## Database Indexes

### B-Tree Indexes (Standard)
- Users: id, email, username, created_at
- Sessions: id, user_id, session_token, expires_at, created_at
- Destinations: id, name, slug, city, country, is_active, created_at
- DestinationSources: id, destination_id, created_at
- Trips: id, user_id, start_date, end_date, created_at
- Itineraries: id, trip_id, version, created_at
- ItineraryStops: id, itinerary_id, destination_id, created_at
- Feedbacks: id, user_id, destination_id, trip_id, created_at

### GiST Indexes (Spatial)
- Destinations: idx_destinations_location on location column

## Repository Layer

Clean abstractions for database access:
- UserRepository: User CRUD operations
- DestinationRepository: Destination operations with spatial query support
- TripRepository: Trip operations
- ItineraryRepository: Itinerary operations with version handling

## Service Layer

Minimal service structure to keep API/domain boundaries clean. Business algorithms are NOT implemented in Phase 1B.

## Testing

Database/domain tests cover:
- Model creation
- Required constraints
- Relationships
- Itinerary version uniqueness
- PostGIS destination geometry
- Basic repository operations
- Migration application

## Future Considerations

- Async SQLAlchemy support (currently sync for Phase 1B)
- Full geospatial query implementation
- Dynamic replanning algorithms
- Route optimization services
- Authentication service integration
- Mapbox integration for mapping/geocoding
