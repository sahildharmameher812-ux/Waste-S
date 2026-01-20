// Render deployment ke liye relative URLs
const API_URL = window.location.origin;

console.log("🌐 Using API URL:", API_URL);

// DOM Elements
const uploadBox = document.getElementById("uploadBox");
const fileInput = document.getElementById("fileInput");
const uploadContent = document.getElementById("uploadContent");
const previewImage = document.getElementById("previewImage");
const classifyBtn = document.getElementById("classifyBtn");
const loading = document.getElementById("loading");
const results = document.getElementById("results");
const resetBtn = document.getElementById("resetBtn");

let selectedFile = null;

// ============ EVENT LISTENERS ============
uploadBox.addEventListener("click", () => {
    fileInput.click();
});

uploadBox.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadBox.style.borderColor = "#00d2ff";
    uploadBox.style.background = "rgba(0, 210, 255, 0.2)";
});

uploadBox.addEventListener("dragleave", () => {
    uploadBox.style.borderColor = "#3a7bd5";
    uploadBox.style.background = "rgba(58, 123, 213, 0.1)";
});

uploadBox.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadBox.style.borderColor = "#3a7bd5";
    uploadBox.style.background = "rgba(58, 123, 213, 0.1)";
    
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
        handleFile(file);
    }
});

fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
});

classifyBtn.addEventListener("click", classifyWaste);
resetBtn.addEventListener("click", resetAll);

// ============ FUNCTIONS ============
function handleFile(file) {
    // File size check (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert("❌ File too large! Max 10MB");
        return;
    }
    
    selectedFile = file;
    
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        previewImage.classList.add("show");
        uploadContent.classList.add("hidden");
    };
    reader.readAsDataURL(file);
    
    classifyBtn.disabled = false;
}

async function classifyWaste() {
    if (!selectedFile) return;
    
    loading.classList.remove("hidden");
    results.classList.add("hidden");
    classifyBtn.disabled = true;
    
    try {
        const formData = new FormData();
        formData.append("file", selectedFile); // Backend expects "file"
        
        console.log("📤 Sending to:", `${API_URL}/classify`);
        
        const response = await fetch(`${API_URL}/classify`, {
            method: "POST",
            body: formData
        });
        
        console.log("📥 Status:", response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server error ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        console.log("✅ Response:", data);
        
        displayResults(data);
        
    } catch (error) {
        console.error("❌ Error:", error);
        alert(`❌ Error: ${error.message}\n\nCheck console (F12) for details.`);
    } finally {
        loading.classList.add("hidden");
        classifyBtn.disabled = false;
    }
}

function displayResults(data) {
    results.classList.remove("hidden");
    
    // Detected object
    document.getElementById("objectName").textContent = data.detected_object;
    document.getElementById("confidence").textContent = data.confidence;
    
    // Category card
    const category = data.waste_category.toLowerCase();
    const categoryCard = document.getElementById("categoryCard");
    categoryCard.className = `category-card ${category}`;
    
    document.getElementById("categoryIcon").textContent = data.dustbin.color.split(" ")[0];
    document.getElementById("categoryName").textContent = data.waste_category;
    document.getElementById("categoryHindi").textContent = data.dustbin.hindi_name;
    document.getElementById("dustbinType").textContent = data.dustbin.type;
    document.getElementById("examples").textContent = data.examples;
    
    // AI Guidance
    const guidanceText = document.getElementById("guidanceText");
    guidanceText.innerHTML = formatGuidance(data.ai_guidance);
    
    // All predictions
    const predictionsList = document.getElementById("predictionsList");
    predictionsList.innerHTML = "";
    
    data.all_predictions.forEach((pred) => {
        const li = document.createElement("li");
        li.innerHTML = `<span>${pred.label}</span><span>${pred.score}</span>`;
        predictionsList.appendChild(li);
    });
    
    results.scrollIntoView({ behavior: "smooth" });
}

function formatGuidance(text) {
    let formatted = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/^• /gm, '<li>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
    
    if (formatted.includes('<li>')) {
        formatted = formatted.replace(/(<li>.*?)(<br>|<\/p>)/g, '$1</li>$2');
        formatted = formatted.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
    }
    
    return `<p>${formatted}</p>`;
}

function resetAll() {
    selectedFile = null;
    fileInput.value = "";
    previewImage.src = "";
    previewImage.classList.remove("show");
    uploadContent.classList.remove("hidden");
    classifyBtn.disabled = true;
    results.classList.add("hidden");
    
    window.scrollTo({ top: 0, behavior: "smooth" });
}

// Health check on load
async function checkBackend() {
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();
        console.log("✅ Backend ready:", data);
    } catch (error) {
        console.warn("⚠️ Backend not ready:", error);
    }
}

window.addEventListener('load', checkBackend);
