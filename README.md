# 🚖 Uber-like API with FastAPI & SQL Server

This project is a **backend API** for an Uber-like ride-hailing service built using **FastAPI**, **SQL Server (Stored Procedures)**, and **JWT authentication**.  

It provides endpoints for **user management, authentication, ride requests, driver management, payments, and role-based access control**.

---

## 📌 Features

- 🔐 **Authentication & Authorization**
  - JWT-based login
  - Role-based access control (`rider`, `driver`, `admin`)
  - OAuth2 scopes for fine-grained permissions

- 👥 **User Management**
  - Register new users
  - Update user profiles
  - Fetch user details
  - Admin-only user listing

- 🚗 **Driver Management**
  - Upload driver documents
  - Update driver location & status
  - Admin verification for drivers
  - Fetch driver details

- 🛺 **Ride Management**
  - Request ride (rider)
  - Accept ride (driver)
  - Complete ride
  - Cancel ride
  - Fetch rides (active, completed, driver-specific)

- 💳 **Payments**
  - Update payment status
  - Fetch payment details

- 🗄 **Database Integration**
  - Uses **SQL Server stored procedures**
  - Database connection managed via `pyodbc`

---

## ⚙️ Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/) – Web framework
- [SQL Server](https://www.microsoft.com/en-us/sql-server) – Database with stored procedures
- [pyodbc](https://github.com/mkleehammer/pyodbc) – SQL Server driver
- [python-jose](https://github.com/mpdavis/python-jose) – JWT handling
- [dotenv](https://github.com/theskumar/python-dotenv) – Environment variables



