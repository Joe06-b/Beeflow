
function initialiserChampsRole() {

    const role = document.getElementById('id_role');

    if (!role) return;

    const champs = {
        admin: document.querySelector(
            '[data-role-field="date_nomination"], .field-date_nomination'
        ),

        apiculteur: document.querySelector(
            '[data-role-field="specialite"], .field-specialite'
        ),

        responsable: document.querySelector(
            '[data-role-field="niveau_experience"], .field-niveau_experience'
        )
    };

    function afficherChamps() {
        const roleSelectionne = role.value;

        for (const [nomRole, champ] of Object.entries(champs)) {
            if (champ) {
                const contientErreur = champ.querySelector(
                    '.errorlist, .text-danger'
                );

                champ.style.display =
                    nomRole === roleSelectionne || contientErreur
                        ? ''
                        : 'none';
            }
        }
    }

    role.addEventListener('change', afficherChamps);
    afficherChamps();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialiserChampsRole);
} else {
    initialiserChampsRole();
}
