# PratiPariksha - Frontend Prototype

**Team 88 | Milestone 2 Submission**

## About This Submission
This folder contains the Frontend-Only implementation of our project. 

There is no Python backend or database required to run this prototype. All API calls, authentication, and database operations have been simulated using browser `localStorage` and a mock JavaScript data layer (`public/js/common.js`).

---

## How to Run the Project

### Recommended Method (VS Code Live Server)
1. Open this `frontend` folder in Visual Studio Code.
2. Install the "Live Server" extension (by Ritwick Dey) if you do not have it.
3. Right-click on `login.html` and select "Open with Live Server".

### Alternative Method (Directly in Browser)
1. Double-click on `login.html` to open it directly in your web browser (Chrome or Safari recommended).

---

## Demo Credentials (Mock Data)

Because the database is mocked in the browser's memory, please use the following credentials to test the role-based routing. 

*Ensure you select the correct **Role** from the dropdown on the login page before clicking login.*

| Role | ID / Username | Password |
| :--- | :--- | :--- |
| **Student** | `S101` | `password123` |
| **Teacher** | `T201` | `password123` |
| **Admin** | `admin` | `admin123` |