/* BARRA DE NAVEGACION (BASE) */

const nav = document.querySelector(".nav"),
    iconoBusqueda = document.querySelector("#iconoBusqueda"), 
    navOpenBtn = document.querySelector(".navOpenBtn"), 
    navCloseBtn = document.querySelector(".navCloseBtn");

iconoBusqueda.addEventListener("click", () => {
    nav.classList.toggle("abrirBusqueda")
    nav.classList.remove("openNav")
    if(nav.classList.contains("abrirBusqueda")) {
        return iconoBusqueda.classList.replace("bx-search", "bx-x");
    }
    iconoBusqueda.classList.replace("bx-x", "bx-search");
});

navOpenBtn.addEventListener("click", () => {
    nav.classList.add("openNav");
    nav.classList.remove("abrirBusqueda")
    iconoBusqueda.classList.replace("bx-x", "bx-search");
})

navCloseBtn.addEventListener("click", () => {
    nav.classList.remove("openNav");
})



/* BARRA DE BUSQUEDA */
document.addEventListener('DOMContentLoaded', function () {
    const searchBox = document.querySelector('#busquedaInput');
    const searchIcon = document.querySelector('#iconoBusqueda2');

    function performSearch() {
        const query = searchBox.value.trim();
        if (query) {
            // Limpia el input
            searchBox.value = '';
            // Redirige a la página de resultados de búsqueda
            window.location.href = `/buscador?query=${encodeURIComponent(query)}`;
        }
    }

    searchBox.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    searchIcon.addEventListener('click', performSearch);
});



/* PERFIL SELECCIONADO */
function mostrarDialogoPerfil(usuario) {
    const dialog = document.getElementById("profile-dialog");

    document.getElementById("profile-foto").src = `/static/uploads/${usuario.foto_perfil}`;
    document.getElementById("profile-nombre").textContent = `${usuario.nombre.toUpperCase()} ${usuario.apellido.toUpperCase()}`;
    document.getElementById("profile-username").textContent = `@${usuario.nombre_usuario}`;
    document.getElementById("profile-bio").textContent = `"${usuario.bio}"`;
    document.getElementById("profile-ubicacion").textContent = usuario.direccion;
    document.getElementById("profile-fecha").textContent = usuario.fecha_nac;

    dialog.showModal();
}

function cerrarDialogoPerfil() {
    const dialog = document.getElementById("profile-dialog");
    dialog.close();
}



/* PERFIL DE USUARIO */
function habilitarEdicion() {
    // Habilitar todos los inputs y selects excepto el email
    var inputs = document.querySelectorAll('input, select, textarea');
    for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].id !== 'correo') {  // No habilitar el campo de correo
            inputs[i].disabled = false;
        }
    }

    // Habilitar el botón "Guardar" y deshabilitar el botón "Editar"
    document.querySelector('.boton-guardar').disabled = false;
    document.querySelector('.boton-editar').disabled = true;
}

function deshabilitarEdicion() {
    // Deshabilitar todos los inputs y selects
    var inputs = document.querySelectorAll('input, select, textarea');
    for (var i = 0; i < inputs.length; i++) {
        inputs[i].disabled = true;
    }

    // Deshabilitar el botón "Guardar" y habilitar el botón "Editar"
    document.querySelector('.boton-guardar').disabled = true;
    document.querySelector('.boton-editar').disabled = false;
}

// Desactivar espaciado en input usuario
function sin_espacio(input) {
    input.value = input.value.replace(/ /g, '');
}








/* CERRAR SESION */
window.history.pushState(null, "", window.location.href);
window.onpopstate = function() {
    window.history.pushState(null, "", window.location.href);
};