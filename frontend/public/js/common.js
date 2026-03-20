// --- 1. MOCK DATABASE (Browser Memory) ---
const MOCK_DATA = {
    students: {
        "S101": { name: "Test Student", password: "password123", points: 550, level: 5, badges: ["Top Performer"], avatar: "public/images/avatars/spark.png" }
    },
    teachers: {
        "T201": { name: "Prof. Sarah", password: "password123", department: "Computer Science" }
    },
    admin: { "admin": "admin123" },
    leaderboard: [
        { rank: 1, name: "Agasthi", marks: 19, points: 1500 },
        { rank: 2, name: "Test Student", marks: 15, points: 550 },
        { rank: 3, name: "Ruhani", marks: 12, points: 300 }
    ],
    // Initial data for tests and questions
    initialTests: [
        { id: 1, test_name: "General Competency Test", date: new Date().toISOString(), status: "started" }
    ],
    initialQuestions: [
        { 
            id: 1, 
            question: "Solve for x: 3x - 7 = 14", 
            type: "MCQ", 
            options: ["x = 5", "x = 7", "x = 9", "x = 21"], 
            correct_answer: "x = 7" 
        },
        { 
            id: 2, 
            question: "What is the value of the square root of 144?", 
            type: "NAT", 
            correct_answer: "12" 
        },
        { 
            id: 3, 
            question: "Which of the following is a prime number?", 
            type: "MCQ", 
            options: ["15", "21", "27", "31"], 
            correct_answer: "31" 
        },
        { 
            id: 4, 
            question: "Calculate the area of a circle with a radius of 7 units (Use π ≈ 3.14)", 
            type: "NAT", 
            correct_answer: "153.86" 
        }
    ]
};

// --- INITIALIZATION (Syncing with Browser Storage) ---
if (!localStorage.getItem('mock_students')) localStorage.setItem('mock_students', JSON.stringify(MOCK_DATA.students));
if (!localStorage.getItem('mock_teachers')) localStorage.setItem('mock_teachers', JSON.stringify(MOCK_DATA.teachers));
if (!localStorage.getItem('mock_tests')) localStorage.setItem('mock_tests', JSON.stringify(MOCK_DATA.initialTests));
if (!localStorage.getItem('mock_questions')) localStorage.setItem('mock_questions', JSON.stringify(MOCK_DATA.initialQuestions));


// --- 2. THE LOGIN HANDLER (Connects to login.html) ---
async function handleLogin(role, username, password) {
    console.log(`Attempting mock login for ${role}: ${username}`);
    
    const res = await fetchAPI('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ role, username, password })
    });

    if (res.ok) {
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('role', data.role);
        localStorage.setItem('username', data.username);
        return true;
    }
    return false;
}


// --- 3. THE FAKE API (Intercepts requests) ---
async function fetchAPI(endpoint, options = {}) {
    const body = JSON.parse(options.body || '{}');

    // MOCK: LOGIN
    if (endpoint === '/auth/login') {
        const students = JSON.parse(localStorage.getItem('mock_students'));
        const teachers = JSON.parse(localStorage.getItem('mock_teachers'));
        
        if (body.role === 'student' && students[body.username]?.password === body.password) {
            return { ok: true, json: () => ({ access_token: "fake-jwt", role: "student", username: students[body.username].name }) };
        } 
        if (body.role === 'teacher' && teachers[body.username]?.password === body.password) {
            return { ok: true, json: () => ({ access_token: "fake-jwt", role: "teacher", username: teachers[body.username].name }) };
        }
        if (body.role === 'admin' && body.username === 'admin' && body.password === 'admin123') {
            return { ok: true, json: () => ({ access_token: "fake-jwt", role: "admin", username: "Admin" }) };
        }
        return { ok: false, status: 401, json: () => ({ msg: "Unauthorized" }) };
    }

    // MOCK: GET ALL TESTS
    if (endpoint === '/student/upcoming-tests' || endpoint === '/teacher/tests') {
        const tests = JSON.parse(localStorage.getItem('mock_tests'));
        return { ok: true, json: () => (tests) };
    }

    // MOCK: CREATE TEST (Teacher)
    if (endpoint === '/teacher/create-test') {
        const tests = JSON.parse(localStorage.getItem('mock_tests'));
        const newTest = { id: tests.length + 1, test_name: body.test_name, date: body.date, status: "started" };
        tests.push(newTest);
        localStorage.setItem('mock_tests', JSON.stringify(tests));
        return { ok: true, json: () => ({ msg: "Test created successfully" }) };
    }

    // MOCK: ADD QUESTION (Teacher)
    if (endpoint === '/teacher/add-question') {
        const questions = JSON.parse(localStorage.getItem('mock_questions'));
        const newQ = { id: questions.length + 1, ...body };
        questions.push(newQ);
        localStorage.setItem('mock_questions', JSON.stringify(questions));
        return { ok: true, json: () => ({ msg: "Question added" }) };
    }

    // MOCK: STUDENT DASHBOARD
    if (endpoint === '/student/dashboard') {
        const students = JSON.parse(localStorage.getItem('mock_students'));
        const user = students["S101"]; 
        return { ok: true, json: () => ({
            total_marks: 15, rank: 2, accuracy: 85, 
            points: user.points, level: user.level, 
            badges: user.badges, avatar: user.avatar
        })};
    }

    // MOCK: GET QUESTIONS
    if (endpoint === '/exam/questions') {
        const questions = JSON.parse(localStorage.getItem('mock_questions'));
        return { ok: true, json: () => (questions) };
    }

    // MOCK: LEADERBOARD (Accessible by all roles)
    if (endpoint === '/student/leaderboard') {
        return { ok: true, json: () => (MOCK_DATA.leaderboard) };
    }

    // MOCK: SHOP PURCHASE
    if (endpoint === '/student/shop/buy') {
        const students = JSON.parse(localStorage.getItem('mock_students'));
        students["S101"].avatar = body.avatar;
        students["S101"].points -= body.price;
        localStorage.setItem('mock_students', JSON.stringify(students));
        return { ok: true, json: () => ({ msg: "Equipped successfully" }) };
    }

    return { ok: true, json: () => ([]) };
}

// --- 4. UTILITY FUNCTIONS ---
function checkRole(role) {
    const currentRole = localStorage.getItem('role');
    if (currentRole !== role && !window.location.href.includes('login.html')) {
        console.warn("Role mismatch simulation.");
    }
}

function logout() {
    localStorage.clear();
    window.location.href = 'login.html';
}