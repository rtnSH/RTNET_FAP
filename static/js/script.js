const appConfig = getAppConfig();
const networkInputs = document.querySelectorAll('input[name="network"]');

initRedmineEntrySplitButton();

document.getElementById('search-btn').addEventListener('click', searchIssue);
document.getElementById('issue-query').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchIssue();
});

networkInputs.forEach((input) => {
    input.addEventListener('change', () => {
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
