"use strict";

const loginForm = document.getElementById("login-form");
const errorMessage = document.getElementById("error-message");
const loginButton = document.getElementById("login-button");

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorMessage.textContent = "";
    loginButton.disabled = true;
    loginButton.textContent = "Signing in...";

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    try {
        await login(username, password);
        window.location.href = "/overview";
    } catch (error) {
        loginButton.disabled = false;
        loginButton.textContent = "Sign In";
        errorMessage.textContent = error.message || "Login failed";
    }
});
