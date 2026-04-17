const appConfig = getAppConfig();
const networkInputs = document.querySelectorAll('input[name="network"]');
const createState = {
    selectedFiles: [],
    optionsDefaults: {
        trackerId: '',
        statusId: '',
        priorityId: ''
    },
    latestOptionsKey: '',
    lastAppliedSubject: '',
    subjectDirty: false,
    lastAppliedDescription: '',
    descriptionDirty: false,
    latestPrefillKey: ''
};

initRedmineEntrySplitButton();
initCreatePanel();

document.getElementById('search-btn').addEventListener('click', searchIssue);
document.getElementById('issue-query').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchIssue();
});

networkInputs.forEach((input) => {
    input.addEventListener('change', () => {
        if (isCreatePanelVisible()) {
            resetCreateDraft({ preserveFeedback: false });
            renderCreateFeedback('info', '네트워크가 변경되어 작성 초안을 새로 불러옵니다.');
            void loadCreateOptions({ preserveSelections: false, preserveFeedback: true });
        }

        if (shouldRefreshRecentIssues()) {
            loadRecentIssues();
        }
    });
});

document.getElementById('back-btn').addEventListener('click', () => {
    document.getElementById('issue-detail').classList.add('hidden');
    document.getElementById('search-list').classList.remove('hidden');
});

loadRecentIssues();

function initRedmineEntrySplitButton() {
    const splitButton = document.querySelector('[data-redmine-entry-split]');
    const toggleButton = document.querySelector('[data-redmine-entry-toggle]');
    const menu = document.querySelector('[data-redmine-entry-menu]');

    if (!splitButton || !toggleButton || !menu) {
        return;
    }

    const closeMenu = () => {
        toggleButton.setAttribute('aria-expanded', 'false');
        menu.hidden = true;
    };

    const openMenu = () => {
        toggleButton.setAttribute('aria-expanded', 'true');
        menu.hidden = false;
    };

    closeMenu();

    toggleButton.addEventListener('click', () => {
        if (menu.hidden) {
            openMenu();
            return;
        }

        closeMenu();
    });

    document.addEventListener('click', (event) => {
        if (!splitButton.contains(event.target)) {
            closeMenu();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeMenu();
            toggleButton.focus();
        }
    });

    menu.querySelectorAll('a').forEach((item) => {
        item.addEventListener('click', closeMenu);
    });
}

function getAppConfig() {
    const { dataset } = document.body;

    return {
        appMode: dataset.appMode || 'development',
        defaultNetwork: dataset.defaultNetwork || 'internal'
    };
}

function getSelectedNetwork() {
    const checkedInput = document.querySelector('input[name="network"]:checked');
    return checkedInput?.value || appConfig.defaultNetwork || 'internal';
}

function shouldRefreshRecentIssues() {
    const issueDetailVisible = !document.getElementById('issue-detail').classList.contains('hidden');
    const hasSearchQuery = document.getElementById('issue-query').value.trim().length > 0;
    return !issueDetailVisible && !hasSearchQuery;
}

function initCreatePanel() {
    const elements = getCreateElements();

    if (!elements.panel || !elements.openButton || !elements.form) {
        return;
    }

    elements.openButton.addEventListener('click', () => {
        void openCreatePanel();
    });

    elements.closeButton?.addEventListener('click', closeCreatePanel);

    elements.form.addEventListener('submit', (event) => {
        event.preventDefault();
        void submitCreateForm();
    });

    elements.project?.addEventListener('change', () => {
        void handleCreateScopeChange();
    });

    elements.tracker?.addEventListener('change', () => {
        void handleCreateScopeChange();
    });

    elements.subject?.addEventListener('input', () => {
        createState.subjectDirty = elements.subject.value !== createState.lastAppliedSubject;
    });

    elements.description?.addEventListener('input', () => {
        createState.descriptionDirty = elements.description.value !== createState.lastAppliedDescription;
    });

    elements.files?.addEventListener('change', handleCreateFileSelection);
    elements.fileList?.addEventListener('click', handleCreateFileListClick);
}

function getCreateElements() {
    return {
        panel: document.getElementById('create-panel'),
        advanced: document.getElementById('create-advanced'),
        openButton: document.getElementById('open-create-btn'),
        closeButton: document.getElementById('close-create-btn'),
        feedback: document.getElementById('create-feedback'),
        form: document.getElementById('create-form'),
        project: document.getElementById('create-project'),
        tracker: document.getElementById('create-tracker'),
        assignee: document.getElementById('create-assignee'),
        status: document.getElementById('create-status'),
        priority: document.getElementById('create-priority'),
        parent: document.getElementById('create-parent'),
        subject: document.getElementById('create-subject'),
        description: document.getElementById('create-description'),
        files: document.getElementById('create-files'),
        fileList: document.getElementById('create-file-list'),
        submitButton: document.getElementById('create-submit-btn')
    };
}

function isCreatePanelVisible() {
    const { panel } = getCreateElements();
    return Boolean(panel && !panel.classList.contains('hidden'));
}

async function openCreatePanel() {
    const elements = getCreateElements();

    if (!elements.panel) {
        return;
    }

    collapseCreateAdvancedSection();
    elements.panel.classList.remove('hidden');
    elements.openButton?.setAttribute('aria-expanded', 'true');

    await loadCreateOptions({ preserveSelections: true });
    elements.panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function closeCreatePanel() {
    const elements = getCreateElements();

    if (!elements.panel) {
        return;
    }

    elements.panel.classList.add('hidden');
    elements.openButton?.setAttribute('aria-expanded', 'false');
    resetCreateDraft();
}

async function loadCreateOptions({ preserveSelections = true, preserveFeedback = false } = {}) {
    const elements = getCreateElements();

    if (!elements.form) {
        return;
    }

    const currentValues = preserveSelections ? {
        projectId: elements.project?.value || '',
        trackerId: elements.tracker?.value || '',
        assigneeKey: elements.assignee?.value || '',
        statusId: elements.status?.value || '',
        priorityId: elements.priority?.value || ''
    } : {
        projectId: '',
        trackerId: '',
        assigneeKey: '',
        statusId: '',
        priorityId: ''
    };
    const requestKey = `${getSelectedNetwork()}:${Date.now()}`;
    createState.latestOptionsKey = requestKey;

    setCreateFormBusy(true, '옵션 불러오는 중...');
    if (!preserveFeedback) {
        renderCreateFeedback('info', '작성 옵션을 불러오는 중입니다.');
    }

    try {
        const network = getSelectedNetwork();
        const response = await fetch(`/api/create/options?network=${network}`);
        const result = await response.json();

        if (createState.latestOptionsKey !== requestKey) {
            return;
        }

        if (!response.ok || result.error) {
            throw new Error(result.error || '작성 옵션을 불러오지 못했습니다.');
        }

        createState.optionsDefaults = {
            trackerId: result.defaults?.tracker?.id ? String(result.defaults.tracker.id) : '',
            statusId: result.defaults?.status?.id ? String(result.defaults.status.id) : '',
            priorityId: result.defaults?.priority?.id ? String(result.defaults.priority.id) : ''
        };

        populateSelect(elements.project, result.projects || [], {
            placeholder: '프로젝트 선택',
            selectedValue: currentValues.projectId,
            labelBuilder: (item) => {
                if (!item?.name) {
                    return '';
                }

                const depth = Number(item?.depth || 0);
                const indentation = depth > 0 ? `${'— '.repeat(depth)}` : '';
                const projectLabel = item.identifier ? `${item.name} (${item.identifier})` : item.name;
                return `${indentation}${projectLabel}`;
            }
        });

        populateSelect(elements.tracker, result.trackers || [], {
            placeholder: '유형 선택',
            selectedValue: currentValues.trackerId || createState.optionsDefaults.trackerId
        });

        populateSelect(elements.assignee, result.assignees || [], {
            placeholder: '담당자 선택',
            valueKey: 'key',
            selectedValue: currentValues.assigneeKey,
            labelBuilder: (item) => item?.label || ''
        });

        populateSelect(elements.status, result.statuses || [], {
            placeholder: '상태 선택',
            selectedValue: currentValues.statusId || createState.optionsDefaults.statusId
        });

        populateSelect(elements.priority, result.priorities || [], {
            placeholder: '우선순위 선택',
            selectedValue: currentValues.priorityId || createState.optionsDefaults.priorityId
        });

        resetCreateParentOptions('프로젝트와 유형을 먼저 선택하세요');

        if (elements.project?.value && elements.tracker?.value) {
            await loadCreatePrefill({ preserveFeedback: true });
            if (elements.feedback?.classList.contains('create-feedback--info')) {
                clearCreateFeedback();
            }
        } else {
            resetCreatePrefillFields();
            clearCreateFeedback();
        }
    } catch (err) {
        if (createState.latestOptionsKey !== requestKey) {
            return;
        }

        renderCreateFeedback('error', `작성 옵션을 불러오지 못했습니다: ${escapeHTML(err.message)}`);
    } finally {
        if (createState.latestOptionsKey === requestKey) {
            setCreateFormBusy(false);
        }
    }
}

async function handleCreateScopeChange() {
    clearCreateFeedback();

    const elements = getCreateElements();
    if (!elements.project?.value || !elements.tracker?.value) {
        resetCreateParentOptions('프로젝트와 유형을 먼저 선택하세요');
        resetCreatePrefillFields();
        return;
    }

    await loadCreatePrefill();
}

async function loadCreatePrefill({ preserveFeedback = false } = {}) {
    const elements = getCreateElements();

    if (!elements.project?.value || !elements.tracker?.value) {
        return;
    }

    const requestKey = `${getSelectedNetwork()}:${elements.project.value}:${elements.tracker.value}:${Date.now()}`;
    createState.latestPrefillKey = requestKey;

    setCreateFormBusy(true, '기본값 불러오는 중...');
    if (!preserveFeedback) {
        renderCreateFeedback('info', '입력 기본값을 불러오는 중입니다.');
    }

    try {
        const network = getSelectedNetwork();
        const response = await fetch(
            `/api/create/prefill?network=${network}&project_id=${encodeURIComponent(elements.project.value)}&tracker_id=${encodeURIComponent(elements.tracker.value)}`
        );
        const result = await response.json();

        if (createState.latestPrefillKey !== requestKey) {
            return;
        }

        if (!response.ok || result.error) {
            throw new Error(result.error || '기본값을 불러오지 못했습니다.');
        }

        applyCreatePrefill(result);

        if (!preserveFeedback) {
            clearCreateFeedback();
        }
    } catch (err) {
        if (createState.latestPrefillKey !== requestKey) {
            return;
        }

        resetCreateParentOptions('상위 일감을 불러오지 못했습니다');
        renderCreateFeedback('error', `기본값을 불러오지 못했습니다: ${escapeHTML(err.message)}`);
    } finally {
        if (createState.latestPrefillKey === requestKey) {
            setCreateFormBusy(false);
        }
    }
}

function applyCreatePrefill(prefill) {
    const elements = getCreateElements();
    const parentOptions = prefill.parent_issue_options || [];
    const defaultParentId = prefill.parent_issue_default_id ? String(prefill.parent_issue_default_id) : '';

    if (parentOptions.length > 0) {
        populateSelect(elements.parent, parentOptions, {
            selectedValue: defaultParentId,
            labelBuilder: (item) => `#${item.id} ${item.subject || ''}`
        });
        elements.parent.disabled = false;
    } else {
        resetCreateParentOptions('선택 가능한 상위 일감이 없습니다');
    }

    if (prefill.default_status?.id && hasSelectValue(elements.status, prefill.default_status.id)) {
        elements.status.value = String(prefill.default_status.id);
    } else if (createState.optionsDefaults.statusId && hasSelectValue(elements.status, createState.optionsDefaults.statusId)) {
        elements.status.value = createState.optionsDefaults.statusId;
    }

    if (prefill.default_priority?.id && hasSelectValue(elements.priority, prefill.default_priority.id)) {
        elements.priority.value = String(prefill.default_priority.id);
    } else if (createState.optionsDefaults.priorityId && hasSelectValue(elements.priority, createState.optionsDefaults.priorityId)) {
        elements.priority.value = createState.optionsDefaults.priorityId;
    }

    applySubjectPrefill(prefill.subject_default || '');
    applyDescriptionPrefill(prefill.default_description || '');
}

function resetCreatePrefillFields() {
    const elements = getCreateElements();

    if ((!createState.subjectDirty || elements.subject?.value === createState.lastAppliedSubject) && elements.subject) {
        elements.subject.value = '';
        createState.lastAppliedSubject = '';
        createState.subjectDirty = false;
    }

    if ((!createState.descriptionDirty || elements.description?.value === createState.lastAppliedDescription) && elements.description) {
        elements.description.value = '';
        createState.lastAppliedDescription = '';
        createState.descriptionDirty = false;
    }

    if (createState.optionsDefaults.statusId && hasSelectValue(elements.status, createState.optionsDefaults.statusId)) {
        elements.status.value = createState.optionsDefaults.statusId;
    }

    if (createState.optionsDefaults.priorityId && hasSelectValue(elements.priority, createState.optionsDefaults.priorityId)) {
        elements.priority.value = createState.optionsDefaults.priorityId;
    }

    if (createState.optionsDefaults.trackerId && hasSelectValue(elements.tracker, createState.optionsDefaults.trackerId)) {
        elements.tracker.value = createState.optionsDefaults.trackerId;
    }
}

function applySubjectPrefill(nextValue) {
    const elements = getCreateElements();

    if (!elements.subject) {
        return;
    }

    const canApply = !createState.subjectDirty || elements.subject.value === createState.lastAppliedSubject;
    if (!canApply) {
        return;
    }

    elements.subject.value = nextValue;
    createState.lastAppliedSubject = nextValue;
    createState.subjectDirty = false;
}

function applyDescriptionPrefill(nextValue) {
    const elements = getCreateElements();

    if (!elements.description) {
        return;
    }

    const canApply = !createState.descriptionDirty || elements.description.value === createState.lastAppliedDescription;
    if (!canApply) {
        return;
    }

    elements.description.value = nextValue;
    createState.lastAppliedDescription = nextValue;
    createState.descriptionDirty = false;
}

async function submitCreateForm() {
    const elements = getCreateElements();
    const formData = new FormData();

    formData.append('project_id', elements.project?.value || '');
    formData.append('tracker_id', elements.tracker?.value || '');
    formData.append('subject', elements.subject?.value || '');
    formData.append('description', elements.description?.value || '');
    formData.append('status_id', elements.status?.value || '');
    formData.append('priority_id', elements.priority?.value || '');
    formData.append('parent_issue_id', elements.parent?.value || '');
    formData.append('assignee_key', elements.assignee?.value || '');

    createState.selectedFiles.forEach((file) => {
        formData.append('files', file, file.name);
    });

    setCreateFormBusy(true, '등록 중...');
    renderCreateFeedback('info', '이슈를 등록하는 중입니다.');

    try {
        const network = getSelectedNetwork();
        const response = await fetch(`/api/issues?network=${network}`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (!response.ok || result.error) {
            throw new Error(result.error || '이슈를 생성하지 못했습니다.');
        }

        const currentScope = {
            projectId: elements.project?.value || '',
            trackerId: elements.tracker?.value || ''
        };

        resetCreateDraft({
            preserveFeedback: true,
            preserveScope: true,
            preserveSelections: true,
            projectId: currentScope.projectId,
            trackerId: currentScope.trackerId
        });
        await loadCreateOptions({ preserveSelections: true, preserveFeedback: true });
        clearCreateFiles();
        renderCreateFeedback('success', buildCreateSuccessMarkup(result));
        document.getElementById('issue-query').value = '';
        loadRecentIssues();
    } catch (err) {
        renderCreateFeedback('error', `이슈를 생성하지 못했습니다: ${escapeHTML(err.message)}`);
    } finally {
        setCreateFormBusy(false);
    }
}

function setCreateFormBusy(isBusy, submitLabel = '이슈 등록') {
    const elements = getCreateElements();

    if (!elements.form) {
        return;
    }

    elements.form.querySelectorAll('input, select, textarea, button').forEach((field) => {
        field.disabled = isBusy;
    });

    if (elements.submitButton) {
        elements.submitButton.textContent = isBusy ? submitLabel : '이슈 등록';
    }
}

function populateSelect(select, items, options = {}) {
    if (!select) {
        return;
    }

    const {
        placeholder = null,
        valueKey = 'id',
        labelKey = 'name',
        labelBuilder = null,
        selectedValue = ''
    } = options;

    select.innerHTML = '';

    if (placeholder !== null) {
        const placeholderOption = document.createElement('option');
        placeholderOption.value = '';
        placeholderOption.textContent = placeholder;
        select.appendChild(placeholderOption);
    }

    items.forEach((item) => {
        const option = document.createElement('option');
        option.value = String(item?.[valueKey] ?? '');
        option.textContent = labelBuilder ? labelBuilder(item) : String(item?.[labelKey] ?? '');
        select.appendChild(option);
    });

    const normalizedSelectedValue = selectedValue ? String(selectedValue) : '';
    if (normalizedSelectedValue && hasSelectValue(select, normalizedSelectedValue)) {
        select.value = normalizedSelectedValue;
    } else if (placeholder !== null) {
        select.value = '';
    } else if (select.options.length > 0) {
        select.selectedIndex = 0;
    }

    select.disabled = items.length === 0;
}

function hasSelectValue(select, value) {
    if (!select) {
        return false;
    }

    const normalizedValue = String(value);
    return Array.from(select.options).some((option) => option.value === normalizedValue);
}

function resetCreateParentOptions(message) {
    const { parent } = getCreateElements();
    populateSelect(parent, [], { placeholder: message });
}

function renderCreateFeedback(type, message) {
    const { feedback } = getCreateElements();

    if (!feedback) {
        return;
    }

    feedback.className = `create-feedback create-feedback--${type}`;
    feedback.innerHTML = message;
}

function clearCreateFeedback() {
    const { feedback } = getCreateElements();

    if (!feedback) {
        return;
    }

    feedback.className = 'create-feedback hidden';
    feedback.innerHTML = '';
}

function buildCreateSuccessMarkup(result) {
    const issueId = escapeHTML(String(result.id || ''));
    const subject = escapeHTML(result.subject || '');
    const internalUrl = escapeHTML(result.redmine_url_internal || '#');
    const externalUrl = escapeHTML(result.redmine_url_external || '#');

    return `
        <div class="create-feedback-title">#${issueId} ${subject} 등록 완료</div>
        <div class="create-feedback-links">
            <a href="${internalUrl}" target="_blank" rel="noopener noreferrer" class="create-feedback-link">내부망에서 열기</a>
            <a href="${externalUrl}" target="_blank" rel="noopener noreferrer" class="create-feedback-link">외부망에서 열기</a>
        </div>
    `;
}

function handleCreateFileSelection(event) {
    const incomingFiles = Array.from(event.target.files || []);
    if (incomingFiles.length === 0) {
        return;
    }

    incomingFiles.forEach((file) => {
        const alreadySelected = createState.selectedFiles.some((selectedFile) => {
            return getFileSignature(selectedFile) === getFileSignature(file);
        });

        if (!alreadySelected) {
            createState.selectedFiles.push(file);
        }
    });

    syncCreateFilesInput();
    renderCreateFileList();
}

function handleCreateFileListClick(event) {
    const removeButton = event.target.closest('[data-remove-file-index]');
    if (!removeButton) {
        return;
    }

    const index = Number(removeButton.dataset.removeFileIndex);
    if (Number.isNaN(index)) {
        return;
    }

    createState.selectedFiles.splice(index, 1);
    syncCreateFilesInput();
    renderCreateFileList();
}

function syncCreateFilesInput() {
    const { files } = getCreateElements();

    if (!files || typeof DataTransfer === 'undefined') {
        return;
    }

    const transfer = new DataTransfer();
    createState.selectedFiles.forEach((file) => {
        transfer.items.add(file);
    });
    files.files = transfer.files;
}

function renderCreateFileList() {
    const { fileList } = getCreateElements();

    if (!fileList) {
        return;
    }

    if (createState.selectedFiles.length === 0) {
        fileList.className = 'create-file-list hidden';
        fileList.innerHTML = '';
        return;
    }

    fileList.className = 'create-file-list';
    fileList.innerHTML = createState.selectedFiles.map((file, index) => `
        <div class="create-file-item">
            <div class="create-file-copy">
                <span class="create-file-name">${escapeHTML(file.name)}</span>
                <span class="create-file-size">${formatFileSize(file.size)}</span>
            </div>
            <button type="button" class="create-file-remove" data-remove-file-index="${index}">제거</button>
        </div>
    `).join('');
}

function clearCreateFiles() {
    createState.selectedFiles = [];
    syncCreateFilesInput();
    renderCreateFileList();
}

function collapseCreateAdvancedSection() {
    const { advanced } = getCreateElements();

    if (advanced) {
        advanced.open = false;
    }
}

function resetCreateDraft(options = {}) {
    const {
        preserveFeedback = false,
        preserveScope = false,
        preserveSelections = false,
        projectId = '',
        trackerId = ''
    } = options;
    const elements = getCreateElements();

    createState.selectedFiles = [];
    createState.latestOptionsKey = '';
    createState.latestPrefillKey = '';
    createState.lastAppliedSubject = '';
    createState.subjectDirty = false;
    createState.lastAppliedDescription = '';
    createState.descriptionDirty = false;

    if (elements.form) {
        elements.form.reset();
    }

    collapseCreateAdvancedSection();

    if (elements.subject) {
        elements.subject.value = '';
    }

    if (elements.description) {
        elements.description.value = '';
    }

    clearCreateFiles();
    resetCreateParentOptions('프로젝트와 유형을 먼저 선택하세요');

    if (!preserveScope) {
        if (elements.project) {
            elements.project.value = '';
        }

        if (elements.tracker) {
            elements.tracker.value = '';
        }
    } else {
        if (elements.project && hasSelectValue(elements.project, projectId)) {
            elements.project.value = String(projectId);
        }

        if (elements.tracker && hasSelectValue(elements.tracker, trackerId)) {
            elements.tracker.value = String(trackerId);
        }
    }

    if (!preserveSelections) {
        if (elements.assignee) {
            elements.assignee.value = '';
        }

        if (elements.status && hasSelectValue(elements.status, createState.optionsDefaults.statusId)) {
            elements.status.value = createState.optionsDefaults.statusId;
        }

        if (elements.priority && hasSelectValue(elements.priority, createState.optionsDefaults.priorityId)) {
            elements.priority.value = createState.optionsDefaults.priorityId;
        }
    }

    if (!preserveFeedback) {
        clearCreateFeedback();
    }
}

function getFileSignature(file) {
    return [file.name, file.size, file.lastModified].join(':');
}

function formatFileSize(size) {
    if (!Number.isFinite(size) || size < 1024) {
        return `${size || 0} B`;
    }

    if (size < 1024 * 1024) {
        return `${(size / 1024).toFixed(1)} KB`;
    }

    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

async function searchIssue() {
    const query = document.getElementById('issue-query').value.trim();
    if (!query) return;

    const network = getSelectedNetwork();
    const loader = document.getElementById('loader');
    const resultArea = document.getElementById('result-area');
    const searchList = document.getElementById('search-list');
    const issueDetail = document.getElementById('issue-detail');
    const errorMsg = document.getElementById('error-msg');

    loader.classList.remove('hidden');
    resultArea.classList.add('hidden');
    searchList.classList.add('hidden');
    issueDetail.classList.add('hidden');
    errorMsg.classList.add('hidden');

    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&network=${network}`);
        const result = await response.json();

        if (result.error) throw new Error(result.error);

        resultArea.classList.remove('hidden');
        if (result.type === 'single') {
            renderIssueDetail(result.data);
            issueDetail.classList.remove('hidden');
            document.getElementById('back-btn').classList.add('hidden');
        } else {
            renderSearchList(result.data, {
                heading: '검색 결과',
                emptyMessage: '검색 결과가 없습니다.'
            });
            searchList.classList.remove('hidden');
        }
    } catch (err) {
        errorMsg.textContent = `오류: ${err.message}`;
        errorMsg.classList.remove('hidden');
    } finally {
        loader.classList.add('hidden');
    }
}

async function loadRecentIssues() {
    const network = getSelectedNetwork();
    const loader = document.getElementById('loader');
    const resultArea = document.getElementById('result-area');
    const searchList = document.getElementById('search-list');
    const issueDetail = document.getElementById('issue-detail');
    const errorMsg = document.getElementById('error-msg');

    loader.classList.remove('hidden');
    resultArea.classList.add('hidden');
    searchList.classList.add('hidden');
    issueDetail.classList.add('hidden');
    errorMsg.classList.add('hidden');

    try {
        const response = await fetch(`/api/recent?network=${network}`);
        const result = await response.json();

        if (result.error) throw new Error(result.error);

        renderSearchList(result.data, {
            heading: '최근 이슈',
            emptyMessage: '최근 이슈가 없습니다.'
        });
        resultArea.classList.remove('hidden');
        searchList.classList.remove('hidden');
    } catch (err) {
        errorMsg.textContent = `오류: ${err.message}`;
        errorMsg.classList.remove('hidden');
    } finally {
        loader.classList.add('hidden');
    }
}

async function viewDetail(issueId) {
    const network = getSelectedNetwork();
    const loader = document.getElementById('loader');
    const searchList = document.getElementById('search-list');
    const issueDetail = document.getElementById('issue-detail');

    loader.classList.remove('hidden');
    try {
        const response = await fetch(`/api/issue/${issueId}?network=${network}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);

        renderIssueDetail(data);
        searchList.classList.add('hidden');
        issueDetail.classList.remove('hidden');
        document.getElementById('back-btn').classList.remove('hidden');
    } catch (err) {
        alert(`상세 정보를 가져오는 중 오류가 발생했습니다: ${err.message}`);
    } finally {
        loader.classList.add('hidden');
    }
}

function renderSearchList(items, options = {}) {
    const container = document.getElementById('list-container');
    const heading = document.querySelector('#search-list h3');
    const headingText = options.heading || '검색 결과';
    const emptyMessage = options.emptyMessage || '검색 결과가 없습니다.';

    if (heading) {
        heading.textContent = headingText;
    }

    container.innerHTML = '';

    if (items.length === 0) {
        container.innerHTML = `<p style="text-align:center; padding: 20px;">${emptyMessage}</p>`;
        return;
    }

    items.forEach(item => {
        const date = new Date(item.updated_on).toLocaleDateString();
        const projectHierarchy = item.project_hierarchy
            ? `<div class="search-item-meta">${escapeHTML(item.project_hierarchy)}</div>`
            : '';
        const html = `
            <div class="search-item" onclick="viewDetail(${item.id})">
                <div class="search-item-header">
                    <div>
                        ${projectHierarchy}
                        <div class="search-item-title">#${item.id} ${escapeHTML(item.subject || '')}</div>
                    </div>
                    <span class="badge">${escapeHTML(item.status || '')}</span>
                </div>
                <div class="search-item-meta">최종 업데이트: ${date}</div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);
    });
}

function renderIssueDetail(data) {
    const network = getSelectedNetwork();

    document.getElementById('res-subject').textContent = `#${data.id} ${data.subject}`;
    document.getElementById('res-status').textContent = data.status;
    document.getElementById('res-author').textContent = data.author;
    document.getElementById('res-assignee').textContent = data.assigned_to;
    document.getElementById('res-priority').textContent = data.priority;

    const internalLink = document.getElementById('res-link-internal');
    const externalLink = document.getElementById('res-link-external');

    if (internalLink && data.redmine_url_internal) {
        internalLink.href = data.redmine_url_internal;
        internalLink.title = data.redmine_url_internal;
    }

    if (externalLink && data.redmine_url_external) {
        externalLink.href = data.redmine_url_external;
        externalLink.title = data.redmine_url_external;
    }

    const resDescription = document.getElementById('res-description');
    if (resDescription) {
        resDescription.innerHTML = processRedmineText(data.description, data.attachments, network) || '설명 없음';
    }

    const existingAttachments = document.querySelector('.attachments-section');
    if (existingAttachments) existingAttachments.remove();

    const attachmentContainer = document.createElement('div');
    attachmentContainer.className = 'attachments-section';
    if (data.attachments && data.attachments.length > 0) {
        attachmentContainer.innerHTML = '<h4>첨부 파일</h4><div class="attachments-grid"></div>';
        const grid = attachmentContainer.querySelector('.attachments-grid');

        data.attachments.forEach(att => {
            const isImage = att.content_type.startsWith('image/');
            const url = `/api/attachment/${att.id}?network=${network}`;

            if (isImage) {
                grid.insertAdjacentHTML('beforeend', `
                    <div class="attachment-item">
                        <a href="${url}" target="_blank">
                            <img src="${url}" alt="${att.filename}" class="attachment-img">
                        </a>
                        <p class="attachment-name">${att.filename}</p>
                    </div>
                `);
            } else {
                grid.insertAdjacentHTML('beforeend', `
                    <div class="attachment-item">
                        <a href="${url}" target="_blank" class="attachment-file-link">
                            📄 ${att.filename}
                        </a>
                    </div>
                `);
            }
        });
        document.getElementById('res-description').after(attachmentContainer);
    }

    const container = document.getElementById('journals-container');
    container.innerHTML = '';

    data.journals.forEach(journal => {
        if (!journal.notes && journal.details.length === 0) return;

        const date = new Date(journal.created_on).toLocaleString();
        const processedNotes = processRedmineText(journal.notes, data.attachments, network);

        const html = `
            <div class="journal-item">
                <div class="journal-header">
                    <span class="journal-user">${journal.user}</span>
                    <span class="journal-date">${date}</span>
                </div>
                ${journal.notes ? `<div class="journal-notes">${processedNotes}</div>` : ''}
                ${journal.details.length > 0 ? `
                    <ul class="journal-details">
                        ${journal.details.map(d => `
                            <li><strong>${d.name || d.property}:</strong> ${d.old_value || '(없음)'} → ${d.new_value}</li>
                        `).join('')}
                    </ul>
                ` : ''}
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);
    });
}

function escapeHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>"']/g, function(m) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[m];
    });
}

function processRedmineText(text, attachments, network) {
    if (!text) return "";

    console.log("Processing text. Available attachments:", attachments.map(a => `${a.filename} (${a.description || ''})`));

    let processed = text.replace(/<img[^>]+src=["']([^"']+)["'][^>]*>/gi, (match, src) => {
        const filename = src.split('/').pop().trim();
        const att = attachments.find(a =>
            a.filename.toLowerCase() === filename.toLowerCase() ||
            (a.description && a.description.toLowerCase() === filename.toLowerCase())
        );
        if (att && att.content_type.startsWith('image/')) {
            const url = `/api/attachment/${att.id}?network=${network}`;
            return match.replace(src, url).replace(/style=["'][^"']*["']/i, (s) => s.includes('width') ? s : s + ' max-width:100%;');
        }
        return match;
    });

    const hasHTML = /<[a-z][\s\S]*>/i.test(processed);
    let escaped = hasHTML ? processed : escapeHTML(processed);

    const regex = /!(\{([^}]*)\})?([<>=])?(\(([^)]*)\))?([^!\n\r]+)!/g;

    return escaped.replace(regex, (match, _fmt, _fmtContent, align, _title, titleContent, filename) => {
        let cleanFilename = filename.trim().replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'");

        const att = attachments.find(a =>
            a.filename.toLowerCase() === cleanFilename.toLowerCase() ||
            (a.description && a.description.toLowerCase() === cleanFilename.toLowerCase()) ||
            a.filename.toLowerCase().includes(cleanFilename.toLowerCase()) ||
            (a.description && a.description.toLowerCase().includes(cleanFilename.toLowerCase()))
        );

        console.log(`Checking tag: ${match}, Clean text: ${cleanFilename}, Matched:`, att ? att.filename : "None");

        if (att && att.content_type.startsWith('image/')) {
            const url = `/api/attachment/${att.id}?network=${network}`;
            let style = 'max-width: 100%; height: auto; border-radius: 4px; border: 1px solid #30363d; margin: 10px 0; display: block;';

            if (align === '<') style += ' float: left; margin-right: 10px;';
            else if (align === '>') style += ' float: right; margin-left: 10px;';
            else if (align === '=') style += ' margin-left: auto; margin-right: auto;';

            return `<img src="${url}" alt="${escapeHTML(att.filename)}" style="${style}" title="${escapeHTML(titleContent || att.filename)}">`;
        }
        return match;
    });
}
