document.addEventListener('DOMContentLoaded', () => {
    const todoList = document.getElementById('todo-list');
    const addForm = document.getElementById('add-todo-form');
    const flashContainer = document.getElementById('flash-container');

    // --- Helper Functions ---

    // Flash 메시지를 동적으로 생성하는 함수
    function showFlashMessage(message, category) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${category} alert-dismissible fade show`;
        alert.role = 'alert';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        flashContainer.appendChild(alert);
        // 잠시 후 자동으로 사라지게 설정
        setTimeout(() => {
            alert.classList.remove('show');
            alert.addEventListener('transitionend', () => alert.remove());
        }, 3000);
    }

    // API 요청을 보내는 범용 함수
    async function apiRequest(url, method = 'POST', body = null) {
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
        const options = { method, headers };
        if (body) {
            options.body = JSON.stringify(body);
        }
        try {
            const response = await fetch(url, options);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || '알 수 없는 오류가 발생했습니다.');
            }
            return data;
        } catch (error) {
            showFlashMessage(error.message, 'danger');
            return null;
        }
    }

    // 새로운 Todo 항목의 HTML을 생성하는 함수
    function createTodoElement(todo) {
        const li = document.createElement('li');
        li.id = `todo-${todo.id}`;
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        if (todo.important && !todo.completed) {
            li.classList.add('bg-warning-subtle');
        }

        const dueDateHtml = todo.due_date && !todo.completed
            ? `<small class="ms-2 due-date text-muted">(마감: ${todo.due_date})</small>`
            : '';

        li.innerHTML = `
            <div>
                <a href="#" class="text-decoration-none me-2 important-btn" data-id="${todo.id}" title="중요도 변경">
                    <i class="${todo.important ? 'fa-solid fa-star text-warning' : 'fa-regular fa-star text-muted'}"></i>
                </a>
                <span class="todo-content" style="${todo.completed ? 'text-decoration: line-through; color: #6c757d;' : ''}">
                    ${todo.content}
                </span>
                ${dueDateHtml}
            </div>
            <div class="d-flex gap-2">
                <a href="#" class="btn btn-sm ${todo.completed ? 'btn-secondary' : 'btn-success'} complete-btn" data-id="${todo.id}" title="${todo.completed ? '완료 취소' : '완료 처리'}">
                    <i class="fa-solid fa-check"></i>
                </a>
                <a href="/edit/${todo.id}" class="btn btn-sm btn-warning" title="수정">
                    <i class="fa-solid fa-pen"></i>
                </a>
                <a href="#" class="btn btn-sm btn-danger delete-btn" data-id="${todo.id}" title="삭제">
                    <i class="fa-solid fa-trash"></i>
                </a>
            </div>
        `;
        return li;
    }


    // --- Event Handlers ---

    // 할 일 추가 처리
    addForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const content = document.getElementById('content-input').value;
        const dueDate = document.getElementById('duedate-input').value;
        const important = document.getElementById('important-input').checked;

        if (!content) {
            showFlashMessage('내용을 입력해주세요.', 'danger');
            return;
        }

        const data = await apiRequest('/add', 'POST', { content, due_date: dueDate, important });
        if (data && data.success) {
            const newTodoElement = createTodoElement(data.todo);
            todoList.appendChild(newTodoElement);
            addForm.reset();
            showFlashMessage('새로운 할 일이 추가되었습니다.', 'success');
            
            const emptyMsg = document.getElementById('empty-todo-msg');
            if(emptyMsg) emptyMsg.remove();
        }
    });

    // 완료, 중요, 삭제 버튼 처리 (이벤트 위임)
    todoList.addEventListener('click', async (e) => {
        const target = e.target.closest('a');
        if (!target) return;

        e.preventDefault();
        const id = target.dataset.id;

        if (target.classList.contains('complete-btn')) {
            const data = await apiRequest(`/complete/${id}`, 'POST');
            if (data && data.success) {
                const todoContent = document.querySelector(`#todo-${id} .todo-content`);
                const dueDateEl = document.querySelector(`#todo-${id} .due-date`);
                todoContent.style.textDecoration = data.completed ? 'line-through' : 'none';
                todoContent.style.color = data.completed ? '#6c757d' : '';
                target.classList.toggle('btn-success');
                target.classList.toggle('btn-secondary');
                if(dueDateEl) dueDateEl.style.display = data.completed ? 'none' : '';
            }
        } else if (target.classList.contains('important-btn')) {
            const data = await apiRequest(`/important/${id}`, 'POST');
            if (data && data.success) {
                const icon = target.querySelector('i');
                icon.classList.toggle('fa-solid');
                icon.classList.toggle('fa-regular');
                icon.classList.toggle('text-warning');
                icon.classList.toggle('text-muted');
                document.getElementById(`todo-${id}`).classList.toggle('bg-warning-subtle', data.important);
            }
        } else if (target.classList.contains('delete-btn')) {
            if (confirm('정말로 이 할 일을 삭제하시겠습니까?')) {
                const data = await apiRequest(`/delete/${id}`, 'POST');
                if (data && data.success) {
                    document.getElementById(`todo-${id}`).remove();
                    showFlashMessage('할 일이 삭제되었습니다.', 'info');
                    
                    if (todoList.children.length === 0) {
                        const li = document.createElement('li');
                        li.id = 'empty-todo-msg';
                        li.className = 'list-group-item text-center';
                        li.textContent = '할 일이 없습니다. 새 할 일을 추가해보세요!';
                        todoList.appendChild(li);
                    }
                }
            }
        }
    });
});