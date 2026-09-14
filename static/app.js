let availableAssets = [];
let currentProject = null;
let currentProjectData = null;
let currentSceneIndex = -1;

async function loadFileList() {
    const res = await fetch('/api/scenes');
    const data = await res.json();
    const list = document.getElementById('file-list');
    list.innerHTML = '';
    data.scenes.forEach(file => {
        const div = document.createElement('div');
        div.className = "px-3 py-2 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 text-sm flex justify-between group";
        const nameSpan = document.createElement('span');
        nameSpan.textContent = file;
        nameSpan.onclick = () => loadProject(file);
        const delBtn = document.createElement('span');
        delBtn.textContent = "×";
        delBtn.className = "text-red-400 font-bold hidden group-hover:block hover:text-red-300";
        delBtn.onclick = async (e) => {
            e.stopPropagation();
            if(confirm(`Delete ${file}?`)) {
                await fetch(`/api/scenes/${file}`, { method: 'DELETE' });
                loadFileList();
            }
        };
        div.appendChild(nameSpan); div.appendChild(delBtn); list.appendChild(div);
    });
}

async function loadAssets() {
    const res = await fetch('/api/assets');
    const data = await res.json();
    availableAssets = data.assets;
    const list = document.getElementById('asset-list');
    list.innerHTML = '';
    data.assets.forEach(file => {
        const div = document.createElement('div');
        div.className = "px-2 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 truncate";
        div.textContent = file;
        div.title = "Click to copy path";
        div.onclick = () => {
            navigator.clipboard.writeText(`assets/${file}`);
            div.textContent = "Copied!";
            setTimeout(() => div.textContent = file, 1000);
        };
        list.appendChild(div);
    });
}

document.getElementById('asset-upload').onchange = async (e) => {
    if(!e.target.files.length) return;
    const formData = new FormData();
    formData.append("file", e.target.files[0]);
    await fetch('/api/upload', { method: 'POST', body: formData });
    loadAssets();
};

async function loadProject(filename) {
    currentProject = filename;
    document.getElementById('current-filename').textContent = filename;
    document.getElementById('empty-state').classList.add('hidden');
    document.getElementById('editor-container').classList.remove('hidden');
    document.getElementById('btn-save').classList.remove('hidden');
    document.getElementById('btn-preview').classList.remove('hidden');
    
    const res = await fetch(`/api/scenes/${filename}`);
    currentProjectData = await res.json();
    renderTimeline();
    document.getElementById('scene-editor').innerHTML = '<p class="text-gray-500 italic">Select a scene from the timeline to edit.</p>';
}

function renderTimeline() {
    const tl = document.getElementById('scenes-timeline');
    tl.innerHTML = '';
    const globalDiv = document.createElement('div');
    globalDiv.className = "p-3 mb-4 bg-gray-800 rounded border border-gray-700 cursor-pointer hover:bg-gray-700";
    globalDiv.innerHTML = `<div class="font-bold text-sm">🎬 Video Settings</div><div class="text-xs text-gray-400">Resolution, FPS, Title</div>`;
    globalDiv.onclick = () => editGlobalSettings();
    tl.appendChild(globalDiv);
    
    currentProjectData.scenes.forEach((scene, i) => {
        const div = document.createElement('div');
        div.className = `scene-card p-3 mb-2 rounded cursor-pointer flex justify-between ${currentSceneIndex === i ? 'bg-gray-700' : ''}`;
        div.innerHTML = `
            <div>
                <div class="font-bold text-sm">${i+1}. ${scene.id}</div>
                <div class="text-xs text-gray-400">${scene.template} | ${scene.duration}s</div>
            </div>
            <div class="flex flex-col gap-1 justify-center">
                <button class="text-xs bg-gray-700 px-1 rounded hover:bg-gray-600" onclick="moveScene(event, ${i}, -1)">▲</button>
                <button class="text-xs bg-gray-700 px-1 rounded hover:bg-gray-600" onclick="moveScene(event, ${i}, 1)">▼</button>
            </div>
        `;
        div.onclick = () => editScene(i);
        tl.appendChild(div);
    });
    
    const addBtn = document.createElement('button');
    addBtn.className = "w-full py-2 bg-gray-800 border border-dashed border-gray-600 rounded text-sm text-gray-400 hover:text-white";
    addBtn.textContent = "+ Add Scene";
    addBtn.onclick = () => {
        currentProjectData.scenes.push({ id: "new_scene", template: "title", duration: 5, data: { title: "New" }});
        renderTimeline();
    };
    tl.appendChild(addBtn);
}

function moveScene(e, index, dir) {
    e.stopPropagation();
    if (index + dir < 0 || index + dir >= currentProjectData.scenes.length) return;
    const temp = currentProjectData.scenes[index];
    currentProjectData.scenes[index] = currentProjectData.scenes[index + dir];
    currentProjectData.scenes[index + dir] = temp;
    if (currentSceneIndex === index) currentSceneIndex = index + dir;
    else if (currentSceneIndex === index + dir) currentSceneIndex = index;
    renderTimeline();
}

function editGlobalSettings() {
    currentSceneIndex = -1; renderTimeline();
    const ed = document.getElementById('scene-editor');
    const video = currentProjectData.video || {};
    ed.innerHTML = `
        <h2 class="text-xl font-bold mb-4 border-b border-gray-700 pb-2">Global Settings</h2>
        <div class="flex flex-col gap-4 max-w-md">
            <div><label class="block text-sm text-gray-400 mb-1">Title</label>
            <input type="text" id="g-title" value="${video.title || ''}" class="w-full bg-dark p-2 rounded border border-gray-700"></div>
            <div class="flex gap-4">
                <div class="flex-1"><label class="block text-sm text-gray-400 mb-1">Width</label>
                <input type="number" id="g-w" value="${video.width || 1920}" class="w-full bg-dark p-2 rounded border border-gray-700"></div>
                <div class="flex-1"><label class="block text-sm text-gray-400 mb-1">Height</label>
                <input type="number" id="g-h" value="${video.height || 1080}" class="w-full bg-dark p-2 rounded border border-gray-700"></div>
            </div>
            <div><label class="block text-sm text-gray-400 mb-1">FPS</label>
            <input type="number" id="g-fps" value="${video.fps || 30}" class="w-full bg-dark p-2 rounded border border-gray-700"></div>
            <button class="bg-gray-700 py-2 rounded text-sm hover:bg-gray-600 mt-4" onclick="saveGlobal()">Apply Changes</button>
        </div>
    `;
}

function saveGlobal() {
    currentProjectData.video = {
        title: document.getElementById('g-title').value,
        width: parseInt(document.getElementById('g-w').value),
        height: parseInt(document.getElementById('g-h').value),
        fps: parseInt(document.getElementById('g-fps').value)
    };
    if (!currentProjectData.config) currentProjectData.config = {};
    currentProjectData.config.bgm_path = document.getElementById('g-bgm').value;
}

function editScene(index) {
    currentSceneIndex = index; renderTimeline();
    const scene = currentProjectData.scenes[index];
    const ed = document.getElementById('scene-editor');
    
    ed.innerHTML = `
        <div class="flex justify-between items-center mb-4 border-b border-gray-700 pb-2">
            <h2 class="text-xl font-bold">Edit Scene: ${scene.id}</h2>
            <button class="text-sm bg-red-900 text-red-200 px-3 py-1 rounded hover:bg-red-800" onclick="deleteCurrentScene()">Delete Scene</button>
        </div>
        <div class="flex flex-col gap-4">
            <div class="flex gap-4">
                <div class="flex-1"><label class="block text-sm text-gray-400 mb-1">ID</label>
                <input type="text" id="s-id" value="${scene.id}" class="w-full bg-dark p-2 rounded border border-gray-700"></div>
                <div class="flex-1"><label class="block text-sm text-gray-400 mb-1">Template</label>
                <select id="s-template" class="w-full bg-dark p-2 rounded border border-gray-700 text-sm">
                    ${['title','comparison','image_text','statistics','ranking','chapter_title','timeline','quote','news_flash','dynamic_captions','social_post','search_typing','lower_third','call_to_action'].map(t => `<option value="${t}" ${t===scene.template?'selected':''}>${t}</option>`).join('')}
                </select></div>
            </div>
            <div class="flex gap-4">
                <div class="flex-1"><label class="block text-sm text-gray-400 mb-1">Duration (s)</label>
                <input type="number" id="s-dur" value="${scene.duration}" class="w-full bg-dark p-2 rounded border border-gray-700"></div>
                <div class="flex-1"><label class="block text-sm text-gray-400 mb-1">Anim In</label>
                <select id="s-in" class="w-full bg-dark p-2 rounded border border-gray-700 text-sm">
                    ${['fadeIn','slideInLeft','slideInRight','slideUp','zoomIn'].map(t => `<option value="${t}" ${t===scene.animation_in?'selected':''}>${t}</option>`).join('')}
                </select></div>
                <div class="flex-1"><label class="block text-sm text-gray-400 mb-1">Anim Out</label>
                <select id="s-out" class="w-full bg-dark p-2 rounded border border-gray-700 text-sm">
                    ${['fadeOut','slideOutLeft','slideOutRight','slideOutDown','zoomOut'].map(t => `<option value="${t}" ${t===scene.animation_out?'selected':''}>${t}</option>`).join('')}
                </select></div>
            </div>
            <div>
                <div class="flex gap-4">
                <div class="flex-1"><label class="block text-sm text-gray-400 mb-1">Video B-Roll</label>
                <select id="s-broll" class="w-full bg-darker p-2 rounded border border-gray-700 text-sm">
                    <option value="">None (Use Gradient)</option>
                    ${availableAssets.filter(a => a.endsWith('.mp4')).map(a => `<option value="assets/${a}" ${'assets/'+a === scene.background_video ? 'selected' : ''}>${a}</option>`).join('')}
                </select></div>
                <div class="flex-1"><label class="block text-sm text-gray-400 mb-1">Image Background</label>
                <select id="s-bgimg" class="w-full bg-darker p-2 rounded border border-gray-700 text-sm">
                    <option value="">None (Use Gradient)</option>
                    ${availableAssets.filter(a => a.endsWith('.png') || a.endsWith('.jpg') || a.endsWith('.jpeg')).map(a => `<option value="assets/${a}" ${'assets/'+a === scene.background_image ? 'selected' : ''}>${a}</option>`).join('')}
                </select></div>
            </div>
            <div>
                <label class="block text-sm text-gray-400 mb-1">Data (JSON)</label>
                <textarea id="s-data" rows="12" class="w-full bg-darker font-mono p-2 rounded border border-gray-700 text-sm">${JSON.stringify(scene.data, null, 2)}</textarea>
            </div>
            <button class="bg-primary text-black font-bold py-2 rounded text-sm hover:bg-blue-400 mt-2" onclick="saveCurrentScene()">Apply Changes</button>
        </div>
    `;
}

function deleteCurrentScene() {
    if(confirm("Delete this scene?")) {
        currentProjectData.scenes.splice(currentSceneIndex, 1);
        currentSceneIndex = -1; renderTimeline();
        document.getElementById('scene-editor').innerHTML = '';
    }
}

function saveCurrentScene() {
    if(currentSceneIndex === -1) return;
    try {
        const dataObj = JSON.parse(document.getElementById('s-data').value);
        currentProjectData.scenes[currentSceneIndex] = {
            ...currentProjectData.scenes[currentSceneIndex],
            id: document.getElementById('s-id').value,
            template: document.getElementById('s-template').value,
            duration: parseFloat(document.getElementById('s-dur').value),
            animation_in: document.getElementById('s-in').value,
            animation_out: document.getElementById('s-out').value,
            background_video: document.getElementById('s-broll').value,
            background_image: document.getElementById('s-bgimg').value,
            data: dataObj
        };
        renderTimeline();
    } catch(e) { alert("Invalid JSON!"); }
}

// Generate New
document.getElementById('btn-generate').onclick = async () => {
    const topic = document.getElementById('new-topic').value;
    const fn = document.getElementById('new-filename').value;
    if(!topic || !fn) return alert("Fill topic and filename");
    const btn = document.getElementById('btn-generate');
    btn.textContent = "Generating..."; btn.disabled = true;
    try {
        await fetch('/api/generate-script', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({topic, duration: 60, filename: fn})});
        await fetch('/api/generate-tts', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({filename: fn})});
        loadFileList(); loadProject(fn);
    } catch(e) { alert("Error: " + e); }
    btn.textContent = "Generate Script & TTS"; btn.disabled = false;
};

document.getElementById('btn-save').onclick = async () => {
    if(!currentProject) return;
    document.getElementById('btn-save').textContent = "Saving...";
    await fetch(`/api/scenes/${currentProject}`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(currentProjectData) });
    setTimeout(() => { document.getElementById('btn-save').textContent = "Save Changes"; }, 1000);
};

// Live Preview
document.getElementById('btn-preview').onclick = async () => {
    if(currentSceneIndex === -1) return alert("Select a scene to preview!");
    document.getElementById('btn-preview').textContent = "Rendering...";
    const scene = currentProjectData.scenes[currentSceneIndex];
    const res = await fetch('/api/preview', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(scene) });
    const data = await res.json();
    document.getElementById('preview-img').src = data.url;
    document.getElementById('preview-modal').classList.remove('hidden');
    document.getElementById('btn-preview').textContent = "Preview Scene";
};

// Render Video
document.getElementById('btn-render').onclick = async () => {
    if(!currentProject) return;
    await fetch(`/api/scenes/${currentProject}`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(currentProjectData) });
    document.getElementById('render-modal').classList.remove('hidden');
    await fetch('/api/render', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({filename: currentProject}) });
};

// Visual Config (Themes)
const THEMES = {
    modern_dark: { start: "#0f0c29", end: "#302b63", primary: "#4fc3f7" },
    cyberpunk: { start: "#2a0845", end: "#6441A5", primary: "#ff007f" },
    minimalist: { start: "#e0e0e0", end: "#ffffff", primary: "#333333" },
    synthwave: { start: "#330066", end: "#ff0066", primary: "#00ffff" },
    nature: { start: "#11998e", end: "#0f3a1f", primary: "#a8ff78" },
    ocean: { start: "#2b5876", end: "#0b132b", primary: "#00d2ff" },
    sunset: { start: "#fc4a1a", end: "#f7b733", primary: "#4a00e0" },
    hacker: { start: "#001100", end: "#003300", primary: "#00ff00" },
    crimson: { start: "#4a0000", end: "#190a05", primary: "#ff3333" },
    neon_night: { start: "#050011", end: "#1a0033", primary: "#cc00ff" },
    corporate: { start: "#ffffff", end: "#e6e9f0", primary: "#0052cc" },
    monochrome: { start: "#1a1a1a", end: "#333333", primary: "#ffffff" }
};

document.getElementById('btn-config').onclick = async () => {
    const res = await fetch('/api/config');
    const cfg = await res.json();
    document.getElementById('cfg-bgm').value = cfg.bgm_path || "";
    document.getElementById('cfg-grad-start').value = cfg.colors?.gradient_start || THEMES.modern_dark.start;
    document.getElementById('cfg-grad-end').value = cfg.colors?.gradient_end || THEMES.modern_dark.end;
    document.getElementById('cfg-primary').value = cfg.colors?.primary || THEMES.modern_dark.primary;
    document.getElementById('config-modal').classList.remove('hidden');
};

document.getElementById('cfg-theme').onchange = (e) => {
    const t = THEMES[e.target.value];
    if(t) {
        document.getElementById('cfg-grad-start').value = t.start;
        document.getElementById('cfg-grad-end').value = t.end;
        document.getElementById('cfg-primary').value = t.primary;
    }
};

document.getElementById('btn-save-config').onclick = async () => {
    const cfg = {
        visual_style: document.getElementById('cfg-theme').value,
        bgm_path: document.getElementById('cfg-bgm').value,
        colors: {
            gradient_start: document.getElementById('cfg-grad-start').value,
            gradient_end: document.getElementById('cfg-grad-end').value,
            primary: document.getElementById('cfg-primary').value
        }
    };
    await fetch('/api/config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(cfg) });
    document.getElementById('config-modal').classList.add('hidden');
};

document.getElementById('btn-videos').onclick = async () => {
    document.getElementById('videos-modal').classList.remove('hidden');
    const res = await fetch('/api/videos');
    const data = await res.json();
    const list = document.getElementById('video-list');
    list.innerHTML = '';
    data.videos.forEach(file => {
        const div = document.createElement('div');
        div.className = "p-3 bg-gray-800 rounded mb-2 cursor-pointer hover:bg-primary hover:text-black transition-colors";
        div.textContent = file;
        div.onclick = () => {
            document.getElementById('video-player').src = `/video/${file}`;
            document.getElementById('video-player').play();
        };
        list.appendChild(div);
    });
};

loadFileList(); loadAssets();

// Override Visual Config loader & saver
document.getElementById('btn-config').onclick = async () => {
    const res = await fetch('/api/config');
    const cfg = await res.json();
    
    // Theme
    document.getElementById('cfg-bgm').value = cfg.bgm_path || "";
    document.getElementById('cfg-grad-start').value = cfg.colors?.gradient_start || THEMES.modern_dark.start;
    document.getElementById('cfg-grad-end').value = cfg.colors?.gradient_end || THEMES.modern_dark.end;
    document.getElementById('cfg-primary').value = cfg.colors?.primary || THEMES.modern_dark.primary;
    
    // Fonts
    const sysReg = document.getElementById('cfg-font-reg');
    const sysBold = document.getElementById('cfg-font-bold');
    sysReg.value = cfg.fonts?.regular || "";
    sysBold.value = cfg.fonts?.bold || "";
    document.getElementById('cfg-font-reg-custom').value = cfg.fonts?.custom_regular || "";
    document.getElementById('cfg-font-bold-custom').value = cfg.fonts?.custom_bold || "";
    
    // AI
    document.getElementById('cfg-ai-prov').value = cfg.provider || "ollama";
    document.getElementById('cfg-ai-model').value = cfg.model || "llama3.2";
    document.getElementById('cfg-ai-url').value = cfg.base_url || "https://api.openai.com/v1";
    document.getElementById('cfg-ai-keyenv').value = cfg.api_key_env || "AI_API_KEY";

    document.getElementById('config-modal').classList.remove('hidden');
};

document.getElementById('btn-save-config').onclick = async () => {
    const cfg = {
        visual_style: document.getElementById('cfg-theme').value,
        bgm_path: document.getElementById('cfg-bgm').value,
        colors: {
            gradient_start: document.getElementById('cfg-grad-start').value,
            gradient_end: document.getElementById('cfg-grad-end').value,
            primary: document.getElementById('cfg-primary').value
        },
        fonts: {
            regular: document.getElementById('cfg-font-reg-custom').value || document.getElementById('cfg-font-reg').value,
            bold: document.getElementById('cfg-font-bold-custom').value || document.getElementById('cfg-font-bold').value,
            custom_regular: document.getElementById('cfg-font-reg-custom').value,
            custom_bold: document.getElementById('cfg-font-bold-custom').value
        },
        provider: document.getElementById('cfg-ai-prov').value,
        model: document.getElementById('cfg-ai-model').value,
        base_url: document.getElementById('cfg-ai-url').value,
        api_key_env: document.getElementById('cfg-ai-keyenv').value
    };
    await fetch('/api/config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(cfg) });
    document.getElementById('config-modal').classList.add('hidden');
};


// Console Logic
let consoleInterval = null;
document.getElementById('btn-console').onclick = () => {
    document.getElementById('console-modal').classList.remove('hidden');
    if(!consoleInterval) {
        consoleInterval = setInterval(async () => {
            if(document.getElementById('console-modal').classList.contains('hidden')) {
                clearInterval(consoleInterval); consoleInterval = null; return;
            }
            try {
                const res = await fetch('/api/logs');
                const data = await res.json();
                const ta = document.getElementById('console-output');
                if(ta.value !== data.logs) {
                    ta.value = data.logs;
                    ta.scrollTop = ta.scrollHeight;
                }
            } catch(e){}
        }, 1000);
    }
};


async function loadFonts() {
    const res = await fetch('/api/fonts');
    const data = await res.json();
    const selReg = document.getElementById('cfg-font-reg');
    const selBold = document.getElementById('cfg-font-bold');
    selReg.innerHTML = '<option value="">-- Select System Font --</option>';
    selBold.innerHTML = '<option value="">-- Select System Font --</option>';
    data.fonts.forEach(f => {
        const name = f.split('/').pop();
        selReg.innerHTML += `<option value="${f}">${name}</option>`;
        selBold.innerHTML += `<option value="${f}">${name}</option>`;
    });
}
loadFonts();
