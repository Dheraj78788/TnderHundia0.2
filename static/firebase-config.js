// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyBnrDnOHIi3oNE9bGBDc2IGt64fZiJgpbQ",
  authDomain: "blink-c30fa.firebaseapp.com",
  projectId: "blink-c30fa",
  storageBucket: "blink-c30fa.firebasestorage.app",
  messagingSenderId: "37798724346",
  appId: "1:37798724346:web:4374e9cfad34dbd69eff43",
  measurementId: "G-T73XD0RSDL"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);