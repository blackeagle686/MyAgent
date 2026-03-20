import { user_api } from "./async.js";


async function loadCurrentUser() {
    try {
        const user = await user_api.get_current_user();  // بدون .data

        const userFullName = document.querySelector(".user-name");
        const userImage = document.querySelector("#UserImageID");

        if (userFullName) {
            const fullName = `${user.user.first_name || ''} ${user.user.last_name || ''}`.trim();
            userFullName.innerText = fullName || "User";
            userImage.src = user.user_image;

        }

        console.log("Current User:", user);
    } catch (err) {
        console.error("Error fetching user:", err);
    }
}

loadCurrentUser();
// document.addEventListener("DOMContentLoaded", loadCurrentUser);
