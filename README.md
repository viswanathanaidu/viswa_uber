# 🚖 Uber-like Ride Hailing API (FastAPI + SQL Server)

This project is a **backend API for an Uber-like ride-hailing service**, built with **FastAPI** and **SQL Server (Stored Procedures)**.  
It demonstrates **scalable API design, clean database integration, and production-ready structure** for interview portfolios.

---

## ✨ Features
- 👤 **User Management**
  - Register new users
  - Login authentication
  - Update profile
  - Fetch user details

- 🚗 **Driver Management**
  - Upload driver documents
  - Update driver status/location
  - Verify driver with vehicle
  - Fetch driver details and ride history

- 🛺 **Ride Management**
  - Request rides (with pickup/dropoff details)
  - Accept rides (drivers)
  - Complete or cancel rides
  - Fetch active and completed rides

- 💳 **Payments**
  - Track and update ride payments
  - Get payment status for a ride

- 🛢 **Database**
  - SQL Server with **Stored Procedures** for core business logic
  - Uses `pyodbc` with `.env` for secure DB connection

## 🔐 Authentication
- This API uses **JWT (JSON Web Tokens)** for secure authentication.
- Login via `/users/login` to get a `Bearer <token>`.
- Include this token in the `Authorization` header for protected endpoints.
---

## 🔐 Authentication & Authorization
- This project uses **JWT (JSON Web Tokens)** for secure authentication.
- **Login** → `/users/login` returns a JWT with role (`rider` or `driver`).
- Include the token in requests:

- **Role-based access control (RBAC):**
- Riders can only:
  - Request rides (`/rides/`)
  - View their active/completed rides
- Drivers can only:
  - Accept rides (`/rides/{ride_id}/accept`)
  - Update their status & location

## 🛠 Tech Stack
- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: SQL Server (`pyodbc` driver)
- **Auth**: Stored procedure-based user authentication
- **Env Management**: `python-dotenv`
- **Data Models**: Pydantic for request/response validation

---

## 📂 Project Structure

