# FastAPI OMSPY Zerodha Broker API Tutorial

This project provides a tutorial demonstrating how to interact with a Zerodha broker account using the `omspy` library, wrapped in a FastAPI application. It covers common trading operations like authentication, placing various order types, modifying and cancelling orders, and fetching account and order information.

**Note:** This tutorial uses mock objects if the `omspy` library is not found or if a live broker connection is not available. This allows the FastAPI application and its endpoints to be explored even without live credentials or `omspy` installed.

## Features Covered

*   **Authentication:** Connecting to the broker (conceptually).
*   **Order Placement:**
    *   Market Orders
    *   Limit Orders
    *   Stop-Loss Limit (SL) Orders
    *   Stop-Loss Market (SL-M) Orders
*   **Order Management:**
    *   Modifying Pending Orders
    *   Cancelling Pending Orders
*   **Information Retrieval:**
    *   Fetching Order History
    *   Getting Status of Specific Orders
    *   Accessing Account Funds & Margins
    *   Viewing Current Positions
    *   Getting Market Quotes for Symbols

## Prerequisites

*   Python 3.7+
*   A Zerodha Kite API account with API key, secret, user ID, password, and 2FA PIN if you intend to adapt this for live trading with `omspy`. (Not required to run this tutorial with its mocks).

## Installation

1.  **Clone the repository (if applicable):**
    ```bash
    # git clone <repository-url>
    # cd <repository-directory>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install fastapi uvicorn omspy python-dotenv
    ```
    *   `fastapi`: For building the API.
    *   `uvicorn`: As an ASGI server to run the FastAPI application.
    *   `omspy`: The Order Management System library for broker interaction (this tutorial includes mocks).
    *   `python-dotenv`: For managing environment variables (recommended for credentials).

## Configuration (for adapting to live trading)

While this tutorial's `/connect` endpoint accepts credentials directly in the request body for simplicity and to work with the mock broker, **for actual use with `omspy` and live trading, never hardcode your credentials.**

It is highly recommended to use environment variables. Create a `.env` file in the project root:

**.env.example:**
```env
ZERODHA_USER_ID="YOUR_USER_ID"
ZERODHA_PASSWORD="YOUR_PASSWORD"
ZERODHA_API_KEY="YOUR_API_KEY"
ZERODHA_API_SECRET="YOUR_API_SECRET"
ZERODHA_PIN="YOUR_2FA_PIN"
```

Rename this to `.env` and fill in your actual Zerodha credentials. You would then modify `tutorial.py` to load these using a library like `python-dotenv` if you were to connect to a live broker.

## Running the Application

1.  Ensure your virtual environment is activated.
2.  Start the FastAPI application using Uvicorn:
    ```bash
    uvicorn tutorial:app --reload
    ```
    The `--reload` flag enables auto-reloading when code changes, useful for development.

3.  Open your browser and navigate to `http://127.0.0.1:8000`.
    You should see the welcome message: `{"message":"Welcome to the omspy Zerodha Broker API Tutorial!","documentation":"/docs", ...}`.

4.  **Access the API documentation (Swagger UI):** `http://127.0.0.1:8000/docs`
    This interface allows you to explore and interact with all the API endpoints defined in the tutorial.

## API Endpoints Summary

The tutorial provides endpoints grouped by functionality. Please explore them via the `/docs` interface. Key categories include:

*   **1. Configuration & Authentication:** Connect to the (mock) broker.
*   **2. Order Object & Attributes:** Understand order parameters.
*   **3. Placing Orders:** Endpoints for Market, Limit, SL, and SL-M orders.
*   **4. Modifying Orders:** Change parameters of pending orders.
*   **5. Cancelling Orders:** Cancel pending orders.
*   **6. Getting Order Information:** Fetch order history and status.
*   **7. Other Useful Features:** Access funds, positions, and market quotes.

Each endpoint in the Swagger UI (`/docs`) has a description explaining its purpose, request parameters, and response structure. The docstrings in `tutorial.py` also provide byte-sized explanations and conceptual `omspy` usage.

## How `omspy` is Used (Conceptual)

This tutorial is designed to show how one *might* structure a FastAPI application to interact with `omspy.brokers.zerodha`.
*   The actual calls to `omspy` methods (e.g., `broker.order_place()`, `broker.funds`) are present in the code.
*   If `omspy` is not installed or if there's an `ImportError`, **mock versions** of the `Zerodha` broker class and `Order` class are used. These mocks simulate the expected behavior and allow the FastAPI application to run and demonstrate its functionality without requiring a live broker connection or `omspy` to be fully configured.
*   To adapt this for live trading, you would remove or bypass the mock objects and ensure `omspy` is correctly installed and configured with your live Zerodha credentials.

## Disclaimer

*   This project is for educational and demonstration purposes only.
*   It is NOT financial advice.
*   Automated trading involves significant risks, including the loss of capital.
*   Always test thoroughly with a paper trading account before attempting to use any trading code with a live brokerage account.
*   The authors and contributors are not responsible for any financial losses incurred.
*   Ensure you understand the broker's terms of service and API usage policies.
```
