// Firebase Web SDK Configuration
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.1/firebase-app.js';
import { getAuth, onAuthStateChanged, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut } from 'https://www.gstatic.com/firebasejs/10.13.1/firebase-auth.js';
import { getDatabase, ref, set, get } from 'https://www.gstatic.com/firebasejs/10.13.1/firebase-database.js';

// Your Firebase config (replace with your actual config)
const firebaseConfig = {
    apiKey: "AIzaSyDScQZuqfUj3i8RGbjj0FkeYYsiibowgrU",
    authDomain: "blink2-c6aae.firebaseapp.com",
    projectId: "blink2-c6aae",
    storageBucket: "blink2-c6aae.firebasestorage.app",
    messagingSenderId: "620469418767",
    appId: "1:620469418767:web:11b28102a4804178819c7a",
    databaseURL: "https://blink2-c6aae-default-rtdb.asia-southeast1.firebasedatabase.app/"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getDatabase(app);

// Auth state observer
onAuthStateChanged(auth, (user) => {
    if (user) {
        console.log('User logged in:', user.uid);
        // Frontend can use this for UI updates
        document.body.setAttribute('data-user', user.uid);
    } else {
        console.log('User logged out');
        document.body.removeAttribute('data-user');
    }
});

// Export auth functions for HTML usage
window.firebaseAuth = {
    signIn: (email, password) => signInWithEmailAndPassword(auth, email, password),
    signUp: (email, password) => createUserWithEmailAndPassword(auth, email, password),
    signOut: () => signOut(auth),
    onAuthStateChanged: onAuthStateChanged
};
