function getcookie(name) {
    let val = null;
    if (document.cookie && document.cookie !== '') {
        const c_list = document.cookie.split(';'); 
        for (let i = 0; i < c_list.length; i++) {
            const c = c_list[i].trim();
            if (c.substring(0, name.length + 1) === (name + '=')) {
                val = decodeURIComponent(c.substring(name.length + 1));
                break;
            }
        }
    }
    return val;
}


async function request(url, method = 'GET', data = null) {
    const options = {
        method: method, 
        headers: {   // ✅
            'Content-Type': 'application/json',
            'X-CSRFToken': getcookie('csrftoken'),
        }
    };
    if (data) {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(url, options);
    if (!response.ok) {
        throw new Error(response.statusText);
    }
    return await response.json();  // ✅ بيرجع JSON عادي
}        

export const api = {
    get: (url) => request(url, 'GET'),
    post: (url, data) => request(url, 'POST', data),
    put: (url, data) => request(url, 'PUT', data),
    delete: (url) => request(url, 'DELETE'),
};


const User_API = "/users/api";


export const user_api = {
    // Normal users
    get_current_user: () => api.get(`${User_API}/user/`),
    get_user_by_id: (id) => api.get(`${User_API}/user/${id}/`),
    get_user_by_username: (username) => api.get(`${User_API}/user/username/${username}/`),
    put_current_user: (data) => api.put(`${User_API}/user/update/`, data),
    post_new_user: (data) => api.post(`${User_API}/user/create/`, data),
    delete_current_user: () => api.delete(`${User_API}/user/delete/`),

    // Admin
    get_all_users: () => api.get(`${User_API}/users/`),
    get_active_users: () => api.get(`${User_API}/users/active/`),
    delete_user_by_id: (id) => api.delete(`${User_API}/users/remove/${id}/`),
    delete_user_by_username: (username) => api.delete(`${User_API}/users/remove/username/${username}/`),
};



// ✨ هنا لازم تعرف الفانكشن
