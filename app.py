# main.py
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, List
import pyodbc
from datetime import datetime,date
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
import pyodbc
from auth import create_access_token, Token,require_role
from datetime import timedelta
from auth import create_access_token, Token, verify_token, TokenData
from fastapi import Security
from auth import verify_token, TokenData
from fastapi.security import OAuth2PasswordRequestForm


# Load environment variables
load_dotenv()

app = FastAPI(
    title="Uber-like API",
    description="API for Uber-like ride hailing service using SQL Server stored procedures",
    version="1.0.0"
)

# Database configuration
def get_db_connection():
    try:
        conn = pyodbc.connect(
            f"Driver={{{os.getenv('DB_DRIVER')}}};"
            f"Server={os.getenv('DB_SERVER')};"
            f"Database={os.getenv('DB_NAME')};"
            f"UID={os.getenv('DB_USER')};"
            f"PWD={os.getenv('DB_PASSWORD')};",
            autocommit=True
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Could not connect to database"
        )

# Helper function to convert rows to dictionaries
def row_to_dict(cursor, row):
    return {column[0]: getattr(row, column[0]) for column in cursor.description}

# Models for request/response validation
class UserBase(BaseModel):
    email: str
    phone_number: str
    password_hash: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None 
    profile_picture_url: Optional[str] = None
    user_type: str

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    user_id: int
    account_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Location(BaseModel):
    latitude: float
    longitude: float

class RideRequest(BaseModel):
    rider_id: int
    pickup_location: Location
    dropoff_location: Location
    pickup_address: str
    dropoff_address: str
    ride_type: str = "standard"

class RideAccept(BaseModel):
    driver_id: int

class DriverLocationUpdate(BaseModel):
    latitude: float
    longitude: float

class DocumentUpload(BaseModel):
    document_type: str
    document_number: str
    document_front_url: str
    document_back_url: Optional[str] = None
    expiry_date: Optional[str] = None

class PaymentRequest(BaseModel):
    payment_method: str
    
class CompleteRideRequest(BaseModel):
    actual_fare: float
class UserUpdate(BaseModel):
    email: Optional[str] = None
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    
class DriverStatusUpdate(BaseModel):
    current_status: str
    
class CancelRideRequest(BaseModel):
    cancelled_by: str  # "rider" or "driver"
    reason: Optional[str] = None
    
class PaymentUpdate(BaseModel):
    payment_status: str  # e.g., "paid", "failed"
    
    
@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, conn = Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        # Call the stored procedure
        cursor.execute("""
            EXEC sp_register_user 
                @email = ?, @phone_number = ?, @password_hash = ?,
                @first_name = ?, @last_name = ?, @date_of_birth = ?,
                @profile_picture_url = ?, @user_type = ?
        """, user.email, user.phone_number, user.password_hash,
           user.first_name, user.last_name, user.date_of_birth,
           user.profile_picture_url, user.user_type)
        
        # Get the result
        columns = [column[0] for column in cursor.description]
        user_data = cursor.fetchone()
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User registration failed"
            )
        
        conn.commit()
        return dict(zip(columns, user_data))

    except pyodbc.DatabaseError as e:
        conn.rollback()
        error_msg = str(e).lower()

        if "email" in error_msg and "already" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered"
            )
        elif "phone" in error_msg and "already" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error: " + str(e)
            )

    finally:
        cursor.close()

@app.post("/users/login", response_model=Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), conn = Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        # Here username = email
        cursor.execute("""
            EXEC sp_authenticate_user @email = ?, @password_hash = ?
        """, form_data.username, form_data.password)

        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        columns = [col[0] for col in cursor.description]
        user_dict = dict(zip(columns, user))

        # 🔑 Map role → scopes
        scopes_map = {
            "rider": ["rider"],
            "driver": ["driver"],
            "admin": ["admin"]
        }

        access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)))
        access_token = create_access_token(
            data={
                "user_id": user_dict["user_id"],
                "email": user_dict["email"],
                "role": user_dict["user_type"],    # keep role
                "scopes": scopes_map.get(user_dict["user_type"], [])  # add scopes ✅
            },
            expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}

    finally:
        cursor.close()


@app.get("/admin/users")
def list_users(
    token_data: TokenData = Security(verify_token, scopes=["admin"]),
    conn = Depends(get_db_connection)
):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, u)) for u in users]
        
@app.post("/drivers/{driver_id}/documents", status_code=status.HTTP_201_CREATED)
def upload_driver_document(
    driver_id: int, 
    document: DocumentUpload, 
    conn = Depends(get_db_connection)
):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            EXEC sp_upload_driver_documents
                @driver_id = ?, @document_type = ?, @document_number = ?,
                @document_front_url = ?, @document_back_url = ?, @expiry_date = ?
        """, driver_id, document.document_type, document.document_number,
           document.document_front_url, document.document_back_url, document.expiry_date)
        
        columns = [column[0] for column in cursor.description]
        result = cursor.fetchall()
        
        conn.commit()
        return [dict(zip(columns, row)) for row in result]
    except pyodbc.DatabaseError as e:
        conn.rollback()
        error_msg = str(e)
        if "already exists" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {error_msg}"
        )
    finally:
        cursor.close()

@app.post("/drivers/{driver_id}/location")
def update_driver_location(
    driver_id: int,
    location: DriverLocationUpdate,
    conn = Depends(get_db_connection)
):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            EXEC sp_update_driver_location
                @driver_id = ?, @latitude = ?, @longitude = ?
        """, driver_id, location.latitude, location.longitude)
        
        # Get the updated driver status
        cursor.execute("SELECT current_status FROM drivers WHERE driver_id = ?", driver_id)
        status_result = cursor.fetchone()
        
        conn.commit()
        return {"status": status_result.current_status}
    except pyodbc.DatabaseError as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    finally:
        cursor.close()
        
@app.post("/rides/", status_code=201)
def request_ride(
    ride: RideRequest,
    token_data: TokenData = Security(verify_token, scopes=["rider"]),
    conn = Depends(get_db_connection)
):
    if ride.rider_id != token_data.user_id:
        raise HTTPException(status_code=403, detail="Cannot request ride for another user")
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            EXEC sp_request_ride
                @rider_id = ?, @pickup_lat = ?, @pickup_lng = ?,
                @dropoff_lat = ?, @dropoff_lng = ?,
                @pickup_address = ?, @dropoff_address = ?,
                @ride_type = ?
        """, ride.rider_id, ride.pickup_location.latitude, ride.pickup_location.longitude,
           ride.dropoff_location.latitude, ride.dropoff_location.longitude,
           ride.pickup_address, ride.dropoff_address, ride.ride_type)
        
        ride_columns = [column[0] for column in cursor.description]
        ride_data = cursor.fetchone()
        if not ride_data:
            raise HTTPException(500, "Failed to create ride")
        
        ride_details = dict(zip(ride_columns, ride_data))
        matched_drivers = []
        if cursor.nextset():
            driver_columns = [column[0] for column in cursor.description]
            matched_drivers = [dict(zip(driver_columns, row)) for row in cursor.fetchall()]
        
        conn.commit()
        return {"ride": ride_details, "matched_drivers": matched_drivers}
    finally:
        cursor.close()

        
@app.post("/drivers/{driver_id}/verify")
def verify_driver(
    driver_id: int,
    token_data: TokenData = Security(verify_token, scopes=["admin"]),
    conn = Depends(get_db_connection)
):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT d.driver_id, v.vehicle_id
            FROM drivers d
            LEFT JOIN vehicles v ON d.driver_id = v.driver_id
            WHERE d.driver_id = ?
        """, driver_id)

        result = cursor.fetchone()
        if not result:
            raise HTTPException(404, "Driver not found")

        driver_id, vehicle_id = result
        if not vehicle_id:
            raise HTTPException(400, "Driver must register a vehicle before verification")

        cursor.execute("""
            UPDATE drivers
            SET is_verified = 1, current_status = 'available'
            WHERE driver_id = ?
        """, driver_id)

        conn.commit()
        return {"message": "Driver verified successfully", "new_status": "available"}
    finally:
        cursor.close()


@app.post("/rides/{ride_id}/accept")
def accept_ride(
    ride_id: int,
    driver: RideAccept,
    token_data: TokenData = Security(verify_token, scopes=["driver"]),
    conn = Depends(get_db_connection)
):
    if driver.driver_id != token_data.user_id:
        raise HTTPException(403, "Cannot accept rides for another driver")

    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT d.is_verified, d.current_status, v.vehicle_id
            FROM drivers d
            LEFT JOIN vehicles v ON d.driver_id = v.driver_id
            WHERE d.driver_id = ?
        """, driver.driver_id)

        result = cursor.fetchone()
        if not result:
            raise HTTPException(400, "Driver not found")

        is_verified, current_status, vehicle_id = result
        if not is_verified:
            raise HTTPException(400, "Driver must be verified before accepting rides")
        if current_status != 'available':
            raise HTTPException(400, f"Driver is currently {current_status}")
        if not vehicle_id:
            raise HTTPException(400, "Driver has no registered vehicle")

        cursor.execute("""
            EXEC sp_accept_ride @ride_id = ?, @driver_id = ?
        """, ride_id, driver.driver_id)

        columns = [column[0] for column in cursor.description]
        ride_details = dict(zip(columns, cursor.fetchone()))

        # convert coords
        for loc in ['pickup', 'dropoff']:
            ride_details[f"{loc}_lat"] = float(ride_details[f"{loc}_lat"])
            ride_details[f"{loc}_lng"] = float(ride_details[f"{loc}_lng"])

        conn.commit()
        return ride_details
    finally:
        cursor.close()

# Pydantic model for request body validation


@app.post("/rides/{ride_id}/complete")
def complete_ride(
    ride_id: int, 
    request: CompleteRideRequest, 
    conn = Depends(get_db_connection)
):
    cursor = conn.cursor()
    try:
        # Verify ride exists and is in progress
        cursor.execute("""
            SELECT driver_id 
            FROM rides 
            WHERE ride_id = ? AND ride_status = 'accepted'
        """, ride_id)
        
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ride not found or not in completable state"
            )
        
        # Update ride
        cursor.execute("""
            UPDATE rides
            SET ride_status = 'completed',
                completed_at = GETDATE(),
                actual_fare = ?
            WHERE ride_id = ?
        """, (request.actual_fare, ride_id))
        
        # Update driver status
        cursor.execute("""
            UPDATE drivers
            SET current_status = 'available'
            WHERE driver_id IN (
                SELECT driver_id FROM rides WHERE ride_id = ?
            )
        """, ride_id)
        
        conn.commit()
        return {"message": "Ride completed successfully"}
        
    except pyodbc.Error as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    finally:
        cursor.close()
        
        
        
@app.patch("/users/{user_id}", status_code=status.HTTP_200_OK)
def update_user_profile(user_id: int, user: UserUpdate, conn = Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            EXEC sp_update_user_profile
                @user_id = ?, @email = ?, @phone_number = ?,
                @first_name = ?, @last_name = ?, @profile_picture_url = ?
        """, user_id, user.email, user.phone_number,
           user.first_name, user.last_name, user.profile_picture_url)

        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        conn.commit()
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, result))
    except pyodbc.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
@app.put("/drivers/{driver_id}/status")
def update_driver_status(driver_id: int, status_update: DriverStatusUpdate, conn = Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE drivers 
            SET current_status = ?
            WHERE driver_id = ?
        """, status_update.current_status, driver_id)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Driver not found")

        conn.commit()
        return {"driver_id": driver_id, "new_status": status_update.current_status}
    except pyodbc.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
@app.patch("/rides/{ride_id}/cancel")
def cancel_ride(ride_id: int, cancel_request: CancelRideRequest, conn = Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE rides
            SET ride_status = 'cancelled',
                cancelled_by = ?,
                cancel_reason = ?,
                cancelled_at = GETDATE()
            WHERE ride_id = ? AND ride_status IN ('requested','accepted')
        """, cancel_request.cancelled_by, cancel_request.reason, ride_id)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=400, detail="Ride not found or cannot be cancelled")

        conn.commit()
        return {"message": f"Ride {ride_id} cancelled successfully"}
    except pyodbc.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        
@app.put("/payments/{ride_id}")
def update_payment_status(ride_id: int, payment: PaymentUpdate, conn = Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE payments
            SET payment_status = ?, updated_at = GETDATE()
            WHERE ride_id = ?
        """, payment.payment_status, ride_id)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Payment record not found")

        conn.commit()
        return {"ride_id": ride_id, "payment_status": payment.payment_status}
    except pyodbc.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, conn=Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", user_id)
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, user))
    finally:
        cursor.close()
@app.get("/drivers/{driver_id}")
def get_driver(driver_id: int, conn=Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM drivers WHERE driver_id = ?", driver_id)
        driver = cursor.fetchone()
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, driver))
    finally:
        cursor.close()
@app.get("/rides/{ride_id}")
def get_ride(ride_id: int, conn=Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM rides WHERE ride_id = ?", ride_id)
        ride = cursor.fetchone()
        if not ride:
            raise HTTPException(status_code=404, detail="Ride not found")
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, ride))
    finally:
        cursor.close()

@app.get("/users/{user_id}/rides/active")
def get_active_rides(user_id: int, conn=Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM rides
            WHERE rider_id = ? AND ride_status IN ('requested', 'accepted', 'in_progress')
        """, user_id)
        rides = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, r)) for r in rides]
    finally:
        cursor.close()

@app.get("/users/{user_id}/rides/completed")
def get_completed_rides(user_id: int, conn=Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM rides
            WHERE rider_id = ? AND ride_status = 'completed'
            ORDER BY completed_at DESC
        """, user_id)
        rides = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, r)) for r in rides]
    finally:
        cursor.close()

@app.get("/drivers/{driver_id}/rides")
def get_driver_rides(driver_id: int, conn=Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM rides
            WHERE driver_id = ?
            ORDER BY requested_at DESC
        """, driver_id)
        rides = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, r)) for r in rides]
    finally:
        cursor.close()
@app.get("/payments/{ride_id}")
def get_payment_status(ride_id: int, conn=Depends(get_db_connection)):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM payments WHERE ride_id = ?", ride_id)
        payment = cursor.fetchone()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment record not found")
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, payment))
    finally:
        cursor.close()

        
        
        
        
        
        
        
        
@app.get("/test-db")
def test_db(conn = Depends(get_db_connection)):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 AS test")
    result = cursor.fetchone()
    return {"database_connection": "successful" if result else "failed"}