// Constants
const rows = 20;
const cols = 15;
const grid = document.getElementById("grid");
const obstacles = [];

for (let r = 1; r < 19; r++) {
    obstacles.push([r, 7]);
}

for (let c = 1; c < 14; c++) {
    obstacles.push([8, c]);
}

const paths = []

for (let c = 1; c < 15; c++) {
    paths.push([0, c]);
}

for (let r = 1; r < 20; r++) {
    paths.push([r, 0]);
}

for (let r = 1; r < 20; r++) {
    paths.push([r, 14]);
}

for(let c = 1; c<15; c++ ){
  paths.push([19,c])
}


const startPos = [0, 0];
const gridData = [];
const xAxis = document.querySelector(".x-axis");
const yAxis = document.querySelector(".y-axis");
const idx2word = ['A','B','C','D','E','F',"G","H","I","J",'K',"L","M","N","P"];

// Status elements
const status = {
  total: document.getElementById("total"),
  occupied: document.getElementById("occupied"),
  available: document.getElementById("available"),
  obstacles: document.getElementById("obstacles"),
  occupancy: document.getElementById("occupancy"),
};

// Initialize the parking grid
function createGrid() {
  grid.innerHTML = "";
  
  // Clear and initialize axes
  if (xAxis) xAxis.innerHTML = "";
  if (yAxis) yAxis.innerHTML = "";
  
  for (let r = 0; r < rows; r++) {
    // Add Y-axis label
    if (yAxis) {
      const yLabel = document.createElement("div");
      yLabel.textContent = r;
      yAxis.appendChild(yLabel);
    }
    
    gridData[r] = [];
    
    for (let c = 0; c < cols; c++) {
      // Add X-axis labels only for first row
      if (r === 0 && xAxis) {
        const xLabel = document.createElement("div");
        xLabel.textContent = idx2word[c] || c;
        xAxis.appendChild(xLabel);
      }
      
      const cell = document.createElement("div");
      cell.classList.add("cell");

      let type = "empty";
      if (r === startPos[0] && c === startPos[1]) {
        type = "start";
      } else if (obstacles.some(([or, oc]) => or === r && oc === c)) {
        type = "obstacle";
      } else if (paths.some(([or,oc])=> or === r && oc === c)){
        type = "path"
      }


      cell.classList.add(type);
      gridData[r][c] = type;
      cell.dataset.row = r;
      cell.dataset.col = c;
      cell.onclick = () => toggleCell(r, c);
      
      // Add visual indicator for start position
      if (type === "start") {
        const marker = document.createElement("span");
        marker.textContent = "S";
        cell.appendChild(marker);
      }
      
      grid.appendChild(cell);
    }
  }
  updateStatus();
}

// Toggle cell state between empty and occupied
async function toggleCell(r, c) {
  const cell = document.querySelector(`.cell[data-row='${r}'][data-col='${c}']`);

  if (!cell || (r === startPos[0] && c === startPos[1]) || gridData[r][c] === "obstacle") {
    return;
  }

  // If empty, show input form to enter number plate
  if (gridData[r][c] === "empty") {
    const inputPlate = prompt("Enter number plate:");
    const plate = inputPlate?.trim();
    if (!plate) return;

    try {
      // Attempt to park the vehicle via backend
      let response;
      try {
        response = await fetch("http://localhost:8000/park_vehicle", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ position: [r, c], plate }),
        });
      } catch (networkError) {
        console.warn("Backend not available, working offline");
        response = { ok: true }; // Simulate success for offline mode
      }

      if (response.ok) {
        // Update UI and grid state
        gridData[r][c] = "occupied";
        cell.classList.remove("empty");
        cell.classList.add("occupied");
        cell.innerHTML = `
          <div class="plate-info">
            <span>${plate}</span>
            <button class="remove-btn">&times;</button>
          </div>
        `;

        // Build position string (e.g., B3)
        const position = idx2word[c] + String(r);

        // Log history (include time!)
        const historyPayload = {
          position: position,
          number_plate: plate,
          status: "Parked",
        };

        const historyResponse = await fetch("http://localhost:8000/history", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(historyPayload)
        });

        // Setup remove button
        const removeBtn = cell.querySelector(".remove-btn");
        if (removeBtn) {
          removeBtn.onclick = (e) => {
            e.stopPropagation();
            removeVehicle(r, c);
          };
        }

        updateStatus();
        showAlert(`Vehicle ${plate} parked successfully!`, "success");
      } else {
        throw new Error("Failed to park vehicle");
      }
    } catch (error) {
      console.error("Error parking vehicle:", error);
      showAlert(error.message || "Failed to park vehicle", "error");
    }
  }
}


async function removeVehicle(r, c) {
  const cell = document.querySelector(`.cell[data-row='${r}'][data-col='${c}']`);
  if (!cell) return;

  try {
    let response;
    try {
      response = await fetch("http://localhost:8000/removed_parked_position", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ position: [r, c] }),
      });
    } catch (networkError) {
      console.warn("Backend not available, working offline");
      response = { ok: true }; // Simulate success
    }

    if (response.ok) {
      const number_plate = cell.querySelector("span")?.textContent.trim() || "UNKNOWN"; 
      const position = idx2word[c] + String(r);      

      // Update UI
      gridData[r][c] = "empty";
      cell.classList.remove("occupied");
      cell.classList.add("empty");
      cell.innerHTML = "";

      updateStatus();

      // Save to history
      const historyData = {
        number_plate: number_plate,
        position: position,
        status: "Unparked",
      };

      await fetch("http://localhost:8000/history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(historyData),
      });

      showAlert("Vehicle removed successfully!", "success");
    } else {
      throw new Error("Failed to remove vehicle");
    }
  } catch (error) {
    console.error("Error removing vehicle:", error);
    showAlert(error.message || "Failed to remove vehicle", "error");
  }
}


// Update the status dashboard
function updateStatus() {
  let total = 0, occupied = 0, obstacleCount = 0, pathCount=0;
  
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const type = gridData[r][c];
      if (type !== "obstacle" && type !== "start") total++;
      if (type === "occupied") occupied++;
      if (type === "obstacle") obstacleCount++;
      if (type === "path") pathCount++;

    }
  }
  
  const available = total - occupied- pathCount;
  const rate = total ? Math.round((occupied / total) * 100) : 0;
  
  // Update status display
  if (status.total) status.total.textContent = total;
  if (status.occupied) status.occupied.textContent = occupied;
  if (status.available) status.available.textContent = available;
  if (status.obstacles) status.obstacles.textContent = obstacleCount;
  if (status.occupancy) status.occupancy.textContent = `${rate}%`;
  
  // Update occupancy color based on percentage
  const occupancyElement = document.getElementById("occupancy");
  if (occupancyElement) {
    if (rate > 80) {
      occupancyElement.style.color = "#e74c3c"; // Red for high occupancy
    } else if (rate > 50) {
      occupancyElement.style.color = "#f39c12"; // Orange for medium occupancy
    } else {
      occupancyElement.style.color = "#2ecc71"; // Green for low occupancy
    }
  }
}

// Detect license plate and allocate parking spot
async function detectPlate() {
  const input = document.getElementById("plateImage");
  const preview = document.getElementById("previewImage");
  const output = document.getElementById("output");
  const file = input?.files?.[0];

  if (!file) {
    showAlert("Please upload an image first.", "warning");
    return;
  }

  // Show loading state
  const detectButton = document.querySelector(".detect-button");
  if (detectButton) {
    detectButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    detectButton.disabled = true;
  }

  // Show uploaded image preview
  if (preview) {
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
  }
  if (output) {
    output.style.display = "none";
  }

  try {
    // Convert image to base64
    const base64Image = await readFileAsDataURL(file);
    
    let detectionData, parkingData;
    
    try {
      // Call API for plate detection
      const detectionResponse = await fetch("http://localhost:8000/predict/base64/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: base64Image }),
      });
      
      detectionData = await detectionResponse.json();
      
      // Find parking spot
      const parkingResponse = await fetch("http://localhost:8000/find_shortest_parking_lot", {
        method: "POST",
      });
      
      parkingData = await parkingResponse.json();
      const x = parkingData['location'][0];
      const y = parkingData['location'][1];
      const position = idx2word[y] + String(x);

      const historyResponse = await fetch("http://localhost:8000/history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
        number_plate: detectionData['plate_texts'][0],
        position: position,
        status: 'Parked',
      })
    })

    } catch (networkError) {
      console.warn("Backend not available, using mock data");
      // Mock data for offline testing
      detectionData = {
        success: true,
        num_plates_detected: 1,
        plate_texts: ["ABC123"],
        result_images: [base64Image.split(',')[1]] // Use uploaded image as result
      };
      

      // Find first empty spot
      let foundSpot = null;
      for (let r = 0; r < rows && !foundSpot; r++) {
        for (let c = 0; c < cols && !foundSpot; c++) {
          if (gridData[r][c] === "empty") {
            foundSpot = [r, c];
          }
        }
      }
      
      parkingData = {
        location: foundSpot || [0, 0]
      };
    }
    
    if (!detectionData.success || detectionData.num_plates_detected <= 0) {
      throw new Error("No license plate detected.");
    }

    // Show detection result
    if (output && detectionData.result_images?.[0]) {
      output.src = "data:image/jpeg;base64," + detectionData.result_images[0];
      output.style.display = "block";
    }
    
    const [x, y] = parkingData.location;
    const plateText = detectionData.plate_texts?.[0] || "UNKNOWN";
    
    // Highlight the allocated spot
    if (x !== undefined && y !== undefined && gridData[x]?.[y] === "empty") {
      highlightParkingSpot(x, y, plateText);
      showAlert("Parking spot allocated successfully!", "success");
    } else {
      showAlert("No available parking spots found.", "warning");
    }
    
  } catch (error) {
    console.error("Error:", error);
    showAlert(error.message || "Something went wrong. Please try again.", "error");
  } finally {
    // Reset button state
    if (detectButton) {
      detectButton.innerHTML = '<i class="fas fa-search"></i> Detect & Allocate Parking';
      detectButton.disabled = false;
    }
  }
}

// Helper function to read file as data URL
function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// Highlight the allocated parking spot
function highlightParkingSpot(x, y, plate) {
  const cell = document.querySelector(`.cell[data-row='${x}'][data-col='${y}']`);
  if (!cell || gridData[x][y] !== "empty") return;
  
  // Mark as occupied
  cell.classList.remove("empty");
  cell.classList.add("occupied");
  cell.innerHTML = `
    <div class="plate-info">
      <span>${plate}</span>
      <button class="remove-btn">&times;</button>
    </div>
  `;
  
  gridData[x][y] = "occupied";
  
  // Add remove button functionality
  const removeBtn = cell.querySelector(".remove-btn");
  if (removeBtn) {
    removeBtn.onclick = (e) => {
      e.stopPropagation();
      removeVehicle(x, y);
    };
  }
  
  // Visual feedback
  cell.style.transform = "scale(1.1)";
  setTimeout(() => {
    cell.style.transform = "scale(1)";
  }, 500);
  
  updateStatus();
}

// Show alert message
function showAlert(message, type = "info") {
  // Remove existing alerts
  const existingAlerts = document.querySelectorAll('.alert');
  existingAlerts.forEach(alert => alert.remove());
  
  const alert = document.createElement("div");
  alert.className = `alert alert-${type}`;
  alert.innerHTML = `
    <span>${message}</span>
    <button onclick="this.parentElement.remove()">&times;</button>
  `;
  
  // Add styles dynamically
  Object.assign(alert.style, {
    position: "fixed",
    top: "20px",
    right: "20px",
    padding: "15px 20px",
    borderRadius: "4px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    zIndex: "1000",
    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
    animation: "slideIn 0.3s ease-out",
    minWidth: "300px"
  });
  
  // Set colors based on type
  if (type === "success") {
    Object.assign(alert.style, {
      backgroundColor: "#d4edda",
      color: "#155724",
      border: "1px solid #c3e6cb"
    });
  } else if (type === "error") {
    Object.assign(alert.style, {
      backgroundColor: "#f8d7da",
      color: "#721c24",
      border: "1px solid #f5c6cb"
    });
  } else if (type === "warning") {
    Object.assign(alert.style, {
      backgroundColor: "#fff3cd",
      color: "#856404",
      border: "1px solid #ffeeba"
    });
  } else {
    Object.assign(alert.style, {
      backgroundColor: "#d1ecf1",
      color: "#0c5460",
      border: "1px solid #bee5eb"
    });
  }
  
  document.body.appendChild(alert);
  
  // Auto remove after 5 seconds
  setTimeout(() => {
    if (alert.parentNode) {
      alert.style.animation = "slideOut 0.3s ease-in";
      setTimeout(() => {
        if (alert.parentNode) alert.remove();
      }, 300);
    }
  }, 5000);
}

// Add keyframe animations for alerts
const style = document.createElement("style");
style.textContent = `
  @keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  @keyframes slideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
  }
`;
document.head.appendChild(style);

// Initialize the application
document.addEventListener("DOMContentLoaded", () => {
  try {
    createGrid();
    console.log("Smart Parking System initialized successfully");
  } catch (error) {
    console.error("Error initializing application:", error);
    showAlert("Failed to initialize parking system", "error");
  }
});

// Make functions globally available
window.detectPlate = detectPlate;
window.toggleCell = toggleCell;
window.removeVehicle = removeVehicle;