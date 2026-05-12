-- Xpediture Database Schema
-- Transition from LocalStorage to Relational Database

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    home_currency CHAR(3) DEFAULT 'USD'
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE trips (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    destination VARCHAR(100),
    currency_code CHAR(3) NOT NULL,
    status VARCHAR(20) CHECK (status IN ('planned', 'ongoing', 'completed')),
    start_date DATE,
    end_date DATE,
    budget DECIMAL(10, 2) DEFAULT 0.00,
    cover_url TEXT,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    trip_id INTEGER NOT NULL,
    title VARCHAR(100) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    category_id INTEGER,
    date DATE NOT NULL,
    CONSTRAINT fk_trip_expense FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
    CONSTRAINT fk_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);

CREATE TABLE checklist_items (
    id SERIAL PRIMARY KEY,
    trip_id INTEGER NOT NULL,
    item_text VARCHAR(255) NOT NULL,
    is_done BOOLEAN DEFAULT FALSE,
    CONSTRAINT fk_trip_checklist FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
);

CREATE TABLE places (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(100),
    city VARCHAR(100),
    category VARCHAR(50),
    rating DECIMAL(2, 1),
    description TEXT
);

CREATE TABLE trip_places (
    trip_id INTEGER NOT NULL,
    place_id INTEGER NOT NULL,
    PRIMARY KEY (trip_id, place_id),
    CONSTRAINT fk_trip_place_trip FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
    CONSTRAINT fk_trip_place_place FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE
);
