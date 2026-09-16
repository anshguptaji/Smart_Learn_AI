document.addEventListener("DOMContentLoaded", () => {

    // =======================
    // ABOUT section fade-in
    // =======================
    const aboutContent = document.querySelector(".about-content");
    if(aboutContent){
        const aboutObserver = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if(entry.isIntersecting){
                    entry.target.classList.add("show");
                }
            });
        }, { threshold: 0.3 });
        aboutObserver.observe(aboutContent);
    }

    // =======================
    // HERO typing effect
    // =======================
    const typedText = document.getElementById("typed-text");
    if(typedText){
        const text = "Welcome to AI-Learning – Smart Approach";
        let index = 0;
        function type() {
            if(index < text.length){
                typedText.innerHTML += text.charAt(index);
                index++;
                setTimeout(type, 80);
            }
        }
        type();
    }

    // =======================
    // Floating hero shapes
    // =======================
    const shapes = document.querySelectorAll(".hero-shapes span");
    shapes.forEach((shape,i)=>{
        let startX = parseFloat(shape.style.left || 0);
        let startY = parseFloat(shape.style.top || 0);
        let amplitude = 30 + Math.random()*20;
        let speed = 0.002 + Math.random()*0.002;

        function animateBlob(time){
            let y = startY + Math.sin(time*speed + i)*amplitude;
            let x = startX + Math.cos(time*speed + i)*amplitude/2;
            shape.style.transform = `translate(${x}px, ${y}px)`;
            requestAnimationFrame(animateBlob);
        }
        requestAnimationFrame(animateBlob);
    });

    // =======================
    // Scroll-triggered animations (cards, steps, about, contact)
    // =======================
    const scrollObserver = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if(entry.isIntersecting){
                entry.target.classList.add("animate-text");
            }
        });
    }, { threshold: 0.2 });
    document.querySelectorAll(".card, .step, .about-content, .contact p").forEach(el => scrollObserver.observe(el));

    // =======================
    // Navbar scroll effect
    // =======================
    const nav = document.querySelector("nav");
    window.addEventListener("scroll", () => {
        if(window.scrollY > 50){
            nav.classList.add("scrolled");
        } else{
            nav.classList.remove("scrolled");
        }
    });

    // =======================
    // HERO button click -> SIGNUP PAGE
    // =======================
    const heroBtn = document.querySelector(".hero-btn");
    if(heroBtn){
        heroBtn.addEventListener("click", () => {
            window.location.href = "/signup";
            // window.location.href = "/signup"; // redirect to signup page
        });
    }

    // =======================
    // Smooth scroll for navbar & footer links
    // =======================
    document.querySelectorAll('nav a, .footer-container a').forEach(link => {
        link.addEventListener('click', function(e){
            const targetId = this.getAttribute('href');
            if(targetId.startsWith('#')){
                e.preventDefault();
                const targetElement = document.querySelector(targetId);
                if(targetElement){
                    window.scrollTo({
                        top: targetElement.offsetTop - 70, // adjust for navbar height
                        behavior: 'smooth'
                    });
                }
            }
        });
    });

    // =======================
    // Signup form simulation
    // =======================
    const signupForm = document.getElementById("signup-form");
    if(signupForm){
        signupForm.addEventListener("submit", (e)=>{
            e.preventDefault();
            alert("Signup successful! (Frontend simulation)");
            signupForm.reset();
        });
    }
    // =======================
// Login form handling
// =======================
const loginForm = document.getElementById("login-form");
if(loginForm){
    loginForm.addEventListener("submit", (e) => {
        e.preventDefault(); // prevent default HTML form submission

        // Get values
        const username = document.getElementById("login-username").value.trim();
        const password = document.getElementById("login-password").value.trim();

        // Simple frontend validation
        if(username === "" || password === ""){
            alert("Please fill in both fields.");
            return;
        }

        // Frontend simulation of login
        alert(`Login successful! Welcome, ${username} (Frontend simulation)`);

        // Reset form
        loginForm.reset();

        // Optionally, redirect to a dashboard page
        // window.location.href = "/dashboard"; // if you have dashboard route in Flask
    });
}

});