tailwind.config = {
  theme: {
    extend: {
      colors: {
        bgPrimary: "var(--bg-primary)",
        panel: "var(--bg-panel)",
        checkbox: "#9CA3AF",
        checkmark: "#1F2937",
        primary: {
          light: "#2563EB",
          dark: "#93C5FD",
        },
        buttonBg: {
          light: "#3B82F6",
          dark: "#1E40AF",
        },
        buttonHover: {
          light: "#2563EB",
          dark: "#1C3AA9",
        },
        dashboardText: {
          light: "#374151",
          dark: "#E5E7EB",
        },
        textPrimary: {
          light: "#1D4ED8",
          dark: "#93C5FD",
        },
      },
    },
  },
};


document.getElementById("theme-toggle").addEventListener("click", function () {
  document.body.classList.toggle("dark-mode");
  document.body.classList.toggle("light-mode");
  const themeIcon = document.getElementById("theme-icon");
  const logo = document.getElementById("logo");
  if (document.body.classList.contains("dark-mode")) {
    themeIcon.classList.remove("fa-moon");
    themeIcon.classList.add("fa-sun");
    logo.src = "{{ url_for('static', filename='dark_logo.png') }}";
  } else {
    themeIcon.classList.remove("fa-sun");
    themeIcon.classList.add("fa-moon");
    logo.src = "{{ url_for('static', filename='min_ai_logo.jpg') }}";
  }
  isDarkMode = document.body.classList.contains("dark-mode"); // Check theme
});

const uploadButton = document.getElementById("uploadButton");
const uploadButton2 = document.getElementById("uploadButton");
const uploadModal = document.getElementById("uploadModal");
const closeModal = document.getElementById("closeModal");
const fileInput = document.getElementById("fileInput");
const sourceList = document.getElementById("sourceList");
const selectAllContainer = document.getElementById("selectAllContainer");
const submitSources = document.getElementById("submitSources");
const selectAll = document.getElementById("selectAll");
const progressBar = document.getElementById("progressBar");
const fileCount = document.getElementById("fileCount");
const chatInput = document.getElementById("chatInput");

var isDarkMode = document.body.classList.contains("dark-mode"); // Check theme
const uploadedFiles = new Map();

function addUserMessage(message) {
  const chatArea = document.getElementById("chatArea");
  const userBubble = document.createElement("div");
  userBubble.className = "chat-bubble user";
  userBubble.textContent = message;
  chatArea.appendChild(userBubble);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function addAIMessage(message) {
  const chatArea = document.getElementById("chatArea");
  const aiBubble = document.createElement("div");
  aiBubble.className = "chat-bubble ai";
  aiBubble.innerHTML = message;
  chatArea.appendChild(aiBubble);
  chatArea.scrollTop = chatArea.scrollHeight;
}

uploadButton.onclick = () => {
  uploadModal.style.display = "flex";
};

closeModal.onclick = () => {
  uploadModal.style.display = "none";
};

fileInput.onchange = () => {
  const files = Array.from(fileInput.files);

  for (const file of files) {
    if (!uploadedFiles.has(file.name)) {
      uploadedFiles.set(file.name, file);
      addSourceToList(file.name);
    }
  }

  const progressPercentage = (uploadedFiles.size / 50) * 100;
  progressBar.style.width = `${Math.min(progressPercentage, 100)}%`;
  fileCount.textContent = `${uploadedFiles.size}/50`;

  if (uploadedFiles.size > 0) {
    selectAllContainer.classList.remove("hidden");
  } else {
    selectAllContainer.classList.add("hidden");
  }

  fileInput.value = "";
};

function addSourceToList(fileName) {
  const sourceItem = document.createElement("div");
  sourceItem.className = "flex items-center justify-between my-2";
  sourceItem.innerHTML = `
        <div class="flex items-center">
            <img src="https://img.icons8.com/color/48/pdf.png" alt="PDF Icon" class="w-5 h-5 mr-2" />
            <span class="text-sm file-name">${fileName}</span>
        </div>
        <input type="checkbox" value="${fileName}" class="form-checkbox text-blue-500" />
    `;
  sourceList.appendChild(sourceItem);
}

selectAll.onchange = () => {
  const checkboxes = sourceList.querySelectorAll("input[type=checkbox]");
  checkboxes.forEach((cb) => (cb.checked = selectAll.checked));
};

function handleSubmission() {
  const selectedFiles = [];
  const formData = new FormData();

  sourceList.querySelectorAll("input[type=checkbox]:checked").forEach((cb) => {
    const file = uploadedFiles.get(cb.value);
    if (file) selectedFiles.push(file);
  });

  const userQuestion = chatInput.value.trim();

  if (!userQuestion) {
    alert("Please enter a question.");
    return;
  }

  addUserMessage(userQuestion);
  chatInput.value = "";

  for (let file of selectedFiles) {
    if (file.size > 50 * 1024 * 1024) {
      alert("File size exceeds the limit of 50MB");
      return;
    }
    formData.append("files", file);
  }
  formData.append("question", userQuestion);

  const chatArea = document.getElementById("chatArea");
  const loadingBubble = document.createElement("div");
  loadingBubble.className = "chat-bubble ai loading";
  loadingBubble.innerHTML = `
    <span class="dot"></span>
    <span class="dot"></span>
    <span class="dot"></span>
`;
  chatArea.appendChild(loadingBubble);
  chatArea.scrollTop = chatArea.scrollHeight;

  fetch("/upload", {
    method: "POST",
    body: formData,
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then((err) => {
          throw new Error(`Failed to submit files: ${err.message || err}`);
        });
      }
      return response.json();
    })
    .then((data) => {
      chatArea.removeChild(loadingBubble);

      if (data.response) {
        addAIMessage(data.response.replace(/\n/g, "<br>"));

        // Add citations if available
        if (data.citations && Array.isArray(data.citations)) {
          addCitations(data.citations);
        }
      } else {
        addAIMessage("No response text received.");
      }
    })
    .catch((error) => {
      console.error("Error:", error);

      chatArea.removeChild(loadingBubble);

      const errorBubble = document.createElement("div");
      errorBubble.className =
        "bg-red-600 text-white p-2 rounded-lg self-start max-w-xs mb-2";
      errorBubble.textContent =
        "There was an error processing your request. Please try again.";
      chatArea.appendChild(errorBubble);
      chatArea.scrollTop = chatArea.scrollHeight;
    });
}

document
  .getElementById("citationToggle")
  .addEventListener("click", function () {
    const dropdown = document.getElementById("citationDropdown");
    const arrow = document.getElementById("citationArrow");

    dropdown.classList.toggle("hidden");

    if (dropdown.classList.contains("hidden")) {
      arrow.classList.replace("fa-angle-down", "fa-angle-right");
    } else {
      arrow.classList.replace("fa-angle-right", "fa-angle-down");
    }
  });

let currentCitations = []; // Store citations globally for re-rendering

// Add citations dynamically
function addCitations(citations) {
  const citationList = document.getElementById("citationList");
  citationList.innerHTML = ""; // Clear previous citations

  if (citations.length === 0) {
    citationList.innerHTML = "<li>No citations available.</li>";
    return;
  }

  // Check theme dynamically inside the function
  const isDarkMode = document.body.classList.contains("dark-mode");

  citations.forEach((citation) => {
    const listItem = document.createElement("li");
    listItem.className =
      "flex items-center justify-between space-x-2 citation-container";

    const link = document.createElement("a");
    link.href = citation;
    link.target = "_blank";
    link.className = `underline hover:text-primary ${
      isDarkMode ? "text-white" : "text-black"
    }`;
    link.textContent = citation;

    const copyIcon = document.createElement("i");
    copyIcon.className = `fas fa-copy cursor-pointer ${
      isDarkMode
        ? "text-gray-200 hover:text-gray-400"
        : "text-gray-800 hover:text-gray-600"
    }`;
    copyIcon.addEventListener("click", () => {
      navigator.clipboard.writeText(citation).then(() => {
        alert("Citation copied to clipboard!");
      });
    });

    listItem.appendChild(link);
    listItem.appendChild(copyIcon);
    citationList.appendChild(listItem);
  });

  citationList.classList.add(
    "space-y-2",
    "flex",
    "flex-col",
    "justify-between"
  );
}

function getCopyButtonClasses() {
  // Check if the current theme is dark or light
  if (document.body.classList.contains("dark-mode")) {
    return "px-2 py-1 text-xs font-medium rounded bg-buttonBg-dark text-white hover:bg-buttonHover-dark";
  } else {
    return "px-2 py-1 text-xs font-medium rounded bg-buttonBg-light text-white hover:bg-buttonHover-light";
  }
}

const style = document.createElement("style");
style.textContent = `
.chat-bubble.ai.loading {
    display: flex;
    gap: 4px;
    align-items: center;
}
.dot {
    width: 8px;
    height: 8px;
    background-color: #fff;
    border-radius: 50%;
    animation: blink 1.4s infinite;
}
.dot:nth-child(2) {
    animation-delay: 0.2s;
}
.dot:nth-child(3) {
    animation-delay: 0.4s;
}
@keyframes blink {
    0%, 80%, 100% {
        opacity: 0;
    }
    40% {
        opacity: 1;
    }
}
`;
document.head.appendChild(style);

submitSources.onclick = handleSubmission;
chatInput.addEventListener("keypress", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    handleSubmission();
  }
});

function resetModal() {
  uploadedFiles.clear();
  sourceList.innerHTML = "";
  progressBar.style.width = "0%";
  fileCount.textContent = "0/50";
  chatInput.value = "";
  uploadModal.style.display = "none";
}

const leftPanel = document.getElementById("leftPanel");
const collapsedPanel = document.getElementById("collapsedPanel");
const addPdfCollapsed = document.getElementById("addPdfCollapsed");

document.getElementById("collapser").addEventListener("click", () => {
  leftPanel.classList.add("hidden");
  collapsedPanel.classList.remove("hidden");
});

addPdfCollapsed.addEventListener("click", () => {
  leftPanel.classList.remove("hidden");
  collapsedPanel.classList.add("hidden");
});

 // Elements
  const deleteChatBtn = document.getElementById('deleteChatBtn');
  const deleteChatModal = document.getElementById('deleteChatModal');
  const deleteConfirmInput = document.getElementById('deleteConfirmInput');
  const confirmDelete = document.getElementById('confirmDelete');
  const cancelDelete = document.getElementById('cancelDelete');
  const successNotification = document.getElementById('successNotification');

  // Function to close the modal
  function closeDeleteModal() {
    deleteChatModal.classList.add('hidden');
    deleteConfirmInput.value = '';
    confirmDelete.disabled = true;
  }

  // Function to show success notification
  function showSuccessNotification() {
    successNotification.classList.remove('hidden');
    successNotification.classList.add('opacity-0');
    setTimeout(() => successNotification.classList.add('opacity-100'), 50);

    setTimeout(() => {
      successNotification.classList.add('opacity-0');
      setTimeout(() => successNotification.classList.add('hidden'), 500);
    }, 3000);
  }

  // Function to update delete modal styles based on theme
  function updateDeleteModalStyles() {
    const modal = deleteChatModal.querySelector('.bg-panel');
    const cancelBtn = document.getElementById('cancelDelete');
    
    // Update modal styles
    modal.style.backgroundColor = 'var(--bg-panel)';
    modal.style.color = 'var(--text-color)';
    deleteConfirmInput.style.backgroundColor = 'var(--input-bg)';
    deleteConfirmInput.style.color = 'var(--input-text-color)';
    deleteConfirmInput.style.borderColor = 'var(--border-color)';
    
    // Update cancel button styles
    if (document.body.classList.contains('dark-mode')) {
        cancelBtn.style.backgroundColor = 'var(--bg-panel)';
        cancelBtn.style.color = '#9CA3AF';  // Gray-400 in dark mode
        cancelBtn.style.border = '1px solid #4B5563';  // Gray-600 in dark mode
        cancelBtn.onmouseover = () => {
            cancelBtn.style.backgroundColor = '#374151';  // Gray-700 in dark mode
        };
        cancelBtn.onmouseout = () => {
            cancelBtn.style.backgroundColor = 'var(--bg-panel)';
        };
    } else {
        cancelBtn.style.backgroundColor = '#F9FAFB';  // Gray-50 in light mode
        cancelBtn.style.color = '#374151';  // Gray-700 in light mode
        cancelBtn.style.border = '1px solid #E5E7EB';  // Gray-200 in light mode
        cancelBtn.onmouseover = () => {
            cancelBtn.style.backgroundColor = '#F3F4F6';  // Gray-100 on hover
        };
        cancelBtn.onmouseout = () => {
            cancelBtn.style.backgroundColor = '#F9FAFB';  // Back to Gray-50
        };
    }
}

// Event listener for theme toggle button
document.getElementById('theme-toggle').addEventListener('click', updateDeleteModalStyles);

// Initialize modal styles when page loads
updateDeleteModalStyles();

  // Open delete modal when delete button is clicked
  deleteChatBtn.addEventListener('click', () => {
    deleteChatModal.classList.remove('hidden');
    updateDeleteModalStyles();  // Apply theme styles when opening
  });

  // Close modal when cancel button is clicked
  cancelDelete.addEventListener('click', closeDeleteModal);

  // Enable delete button when 'delete' is typed
  deleteConfirmInput.addEventListener('input', (e) => {
    confirmDelete.disabled = e.target.value.trim() !== 'delete';
  });

  // Handle confirm delete action
  confirmDelete.addEventListener('click', async () => {
    try {
      const response = await fetch('/delete-chat', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        document.getElementById('chatArea').innerHTML = '';
        closeDeleteModal();
        showSuccessNotification();
      } else {
        throw new Error('Failed to delete chat history');
      }
    } catch (error) {
      alert('Failed to delete chat history. Please try again.');
    }
  });

  // Close modal when escape key is pressed
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDeleteModal();
  });

  // Close modal when clicked outside of the modal
  deleteChatModal.addEventListener('click', (e) => {
    if (e.target === deleteChatModal) closeDeleteModal();
  });

  