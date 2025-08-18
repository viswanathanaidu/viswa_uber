USE [uber_ride]
GO
CREATE PROCEDURE sp_upload_driver_documents
    @driver_id INT,
    @document_type VARCHAR(20),
    @document_number NVARCHAR(100),
    @document_front_url NVARCHAR(255),
    @document_back_url NVARCHAR(255) = NULL,
    @expiry_date DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Check if driver exists
        IF NOT EXISTS (SELECT 1 FROM drivers WHERE driver_id = @driver_id)
        BEGIN
            RAISERROR('Driver not found', 16, 1);
        END
        
        -- Check if document type already exists for this driver
        IF EXISTS (
            SELECT 1 FROM driver_documents 
            WHERE driver_id = @driver_id AND document_type = @document_type
        )
        BEGIN
            RAISERROR('Document type already exists for this driver', 16, 1);
        END
        
        -- Insert document
        INSERT INTO driver_documents (
            driver_id, document_type, document_number,
            document_front_url, document_back_url, expiry_date
        )
        VALUES (
            @driver_id, @document_type, @document_number,
            @document_front_url, @document_back_url, @expiry_date
        );
        
        -- If all required documents are uploaded, mark driver as verified
        DECLARE @required_docs INT = 4; -- license, aadhaar, pan, rc
        DECLARE @uploaded_docs INT;
        
        SELECT @uploaded_docs = COUNT(*) 
        FROM driver_documents 
        WHERE driver_id = @driver_id 
        AND verification_status = 'verified';
        
        IF @uploaded_docs >= @required_docs
        BEGIN
            UPDATE drivers SET is_verified = 1 WHERE driver_id = @driver_id;
        END
        
        COMMIT TRANSACTION;
        
        SELECT * FROM driver_documents WHERE driver_id = @driver_id;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
            
        THROW;
    END CATCH
END;

select * from driver_documents