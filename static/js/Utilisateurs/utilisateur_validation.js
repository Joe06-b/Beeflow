/**
 * ====================================================================
 * BeeFlow - Contrôle de saisie du formulaire Utilisateur (Ajout & Modification)
 * Fichier : static/js/Utilisateurs/utilisateur_validation.js
 * ====================================================================
 */

(function () {
    'use strict';

    function initUserFormValidation() {
        // Cibler précisément le formulaire du backoffice utilisateur (et ignorer le modal #profileForm du header)
        const form = document.querySelector('.card-body form') ||
                     document.querySelector('form:not(#profileForm)[method="post"]');

        if (!form) {
            return;
        }

        // Désactiver la validation HTML5 native pour avoir un contrôle personnalisé unifié
        form.setAttribute('novalidate', 'true');

        // Détection du mode : Ajout vs Modification
        const currentUrl = window.location.pathname;
        const isEditMode = currentUrl.includes('/modifier/') ||
                           (document.querySelector('.card-header h2')?.textContent.toLowerCase().includes('modifier')) ||
                           (form.querySelector('button[type="submit"]')?.textContent.toLowerCase().includes('enregistrer'));

        // Récupération des champs du formulaire
        const getField = (id) => document.getElementById(id);

        const fields = {
            username: getField('id_username'),
            email: getField('id_email'),
            firstName: getField('id_first_name'),
            lastName: getField('id_last_name'),
            telephone: getField('id_telephone'),
            dateNaissance: getField('id_date_naissance'),
            role: getField('id_role'),
            sexe: getField('id_sexe'),
            statut: getField('id_statut'),
            dateNomination: getField('id_date_nomination'),
            specialite: getField('id_specialite'),
            niveauExperience: getField('id_niveau_experience')
        };

        const rulesPanel = document.getElementById('user-rules');
        if (rulesPanel) {
            const rules = {
                identifiants: () => fields.username && fields.email && fields.telephone && fields.username.value.trim() && fields.email.value.trim() && fields.telephone.value.trim() ? 'ok' : 'pending',
                identite: () => fields.firstName && fields.lastName && fields.firstName.value.trim() && fields.lastName.value.trim() ? 'ok' : 'pending',
                profil: () => fields.role && fields.statut && fields.sexe && fields.role.value && fields.statut.value && fields.sexe.value ? 'ok' : 'pending',
                naissance: () => !fields.dateNaissance || !fields.dateNaissance.value ? 'pending' : 'ok',
                role: () => fields.role && fields.role.value ? 'ok' : 'pending'
            };
            const items = [...rulesPanel.querySelectorAll('[data-rule]')];
            const score = document.getElementById('userRulesScore');
            const updateRules = () => {
                let ok = 0;
                items.forEach(item => {
                    const state = rules[item.dataset.rule]();
                    item.className = 'is-' + state;
                    if (state === 'ok') ok++;
                });
                score.textContent = ok ? `${ok}/${items.length}` : '';
                score.className = 'user-rules-score' + (ok === items.length ? ' is-complete' : '');
                rulesPanel.classList.toggle('is-complete', ok === items.length);
            };
            form.addEventListener('input', updateRules);
            form.addEventListener('change', updateRules);
            updateRules();
        }

        // Gestion de l'affichage des erreurs
        function getErrorElement(input) {
            if (!input) return null;
            const container = input.closest('[data-role-field]') || input.parentElement;
            let errorEl = container.querySelector('.bf-field-error');
            if (!errorEl) {
                errorEl = document.createElement('div');
                errorEl.className = 'bf-field-error';
                errorEl.style.color = '#dc3545';
                errorEl.style.fontSize = '12px';
                errorEl.style.fontWeight = '500';
                errorEl.style.marginTop = '5px';
                errorEl.style.display = 'none';
                container.appendChild(errorEl);
            }
            return errorEl;
        }

        function showFieldError(input, message) {
            if (!input) return;
            input.style.borderColor = '#dc3545';
            input.style.backgroundColor = '#fff8f8';
            input.style.boxShadow = '0 0 0 3px rgba(220, 53, 69, 0.15)';

            const errorEl = getErrorElement(input);
            if (errorEl) {
                errorEl.innerHTML = `<span style="margin-right: 4px;">⚠️</span> ${message}`;
                errorEl.style.display = 'block';
            }
        }

        function clearFieldError(input) {
            if (!input) return;
            input.style.borderColor = '#198754';
            input.style.backgroundColor = '#f8fff9';
            input.style.boxShadow = '0 0 0 3px rgba(25, 135, 84, 0.12)';

            const errorEl = getErrorElement(input);
            if (errorEl) {
                errorEl.textContent = '';
                errorEl.style.display = 'none';
            }
        }

        function resetFieldStyle(input) {
            if (!input) return;
            input.style.borderColor = '';
            input.style.backgroundColor = '';
            input.style.boxShadow = '';

            const errorEl = getErrorElement(input);
            if (errorEl) {
                errorEl.textContent = '';
                errorEl.style.display = 'none';
            }
        }

        // Vérifie si le champ est actuellement visible (notamment pour les champs conditionnels de rôle)
        function isFieldVisible(input) {
            if (!input) return false;
            const parent = input.closest('[data-role-field]');
            if (parent && (parent.style.display === 'none' || window.getComputedStyle(parent).display === 'none')) {
                return false;
            }
            return input.offsetParent !== null;
        }

        // ==========================================
        // RÈGLES DE VALIDATION UNITAIRES
        // ==========================================

        function validateUsername() {
            const input = fields.username;
            if (!input) return true;
            const val = input.value.trim();

            if (!val) {
                showFieldError(input, "Le nom d'utilisateur est obligatoire.");
                return false;
            }
            if (val.length < 4) {
                showFieldError(input, "Le nom d'utilisateur doit contenir au moins 4 caractères.");
                return false;
            }
            if (val.length > 150) {
                showFieldError(input, "Le nom d'utilisateur ne peut pas dépasser 150 caractères.");
                return false;
            }
            // AbstractUser: lettres, chiffres, et @/./+/-/_
            if (!/^[\w.@+-]+$/.test(val)) {
                showFieldError(input, "Caractères autorisés : lettres, chiffres et @/./+/-/_ (pas d'espaces).");
                return false;
            }

            clearFieldError(input);
            return true;
        }

        function validateEmail() {
            const input = fields.email;
            if (!input) return true;
            const val = input.value.trim();

            if (!val) {
                showFieldError(input, "L'adresse e-mail est obligatoire.");
                return false;
            }
            // Format email standard
            const emailRegex = /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/;
            if (!emailRegex.test(val)) {
                showFieldError(input, "Veuillez entrer une adresse e-mail valide (ex: apiculteur@beeflow.fr).");
                return false;
            }

            clearFieldError(input);
            return true;
        }

        function validateFirstName() {
            const input = fields.firstName;
            if (!input) return true;
            const val = input.value.trim();

            if (val) {
                if (val.length < 2) {
                    showFieldError(input, "Le prénom doit comporter au moins 2 lettres.");
                    return false;
                }
                if (!/^[a-zA-ZÀ-ÿ\s'-]+$/.test(val)) {
                    showFieldError(input, "Le prénom ne doit contenir que des lettres.");
                    return false;
                }
                clearFieldError(input);
            } else {
                resetFieldStyle(input);
            }
            return true;
        }

        function validateLastName() {
            const input = fields.lastName;
            if (!input) return true;
            const val = input.value.trim();

            if (val) {
                if (val.length < 2) {
                    showFieldError(input, "Le nom doit comporter au moins 2 lettres.");
                    return false;
                }
                if (!/^[a-zA-ZÀ-ÿ\s'-]+$/.test(val)) {
                    showFieldError(input, "Le nom ne doit contenir que des lettres.");
                    return false;
                }
                clearFieldError(input);
            } else {
                resetFieldStyle(input);
            }
            return true;
        }

        function validateTelephone() {
            const input = fields.telephone;
            if (!input) return true;
            const rawVal = input.value.trim();

            if (!rawVal) {
                showFieldError(input, "Le numéro de téléphone est obligatoire.");
                return false;
            }

            // Supprimer les espaces éventuels pour vérifier la conformité du modèle (^\+?[0-9]{8,12}$)
            const cleanPhone = rawVal.replace(/\s+/g, '');
            if (!/^\+?[0-9]{8,12}$/.test(cleanPhone)) {
                showFieldError(input, "Numéro invalide : doit comporter 8 à 12 chiffres (ex: +21612345678 ou 12345678).");
                return false;
            }
            clearFieldError(input);
            return true;
        }

        function validateDateNaissance() {
            const input = fields.dateNaissance;
            if (!input) return true;
            const val = input.value;

            if (!val) {
                showFieldError(input, "La date de naissance est obligatoire.");
                return false;
            }

            // val est au format YYYY-MM-DD
            const parts = val.split('-');
            if (parts.length === 3) {
                const birthYear = parseInt(parts[0], 10);
                const birthMonth = parseInt(parts[1], 10) - 1;
                const birthDay = parseInt(parts[2], 10);
                const birthDate = new Date(birthYear, birthMonth, birthDay);

                const today = new Date();
                today.setHours(0, 0, 0, 0);

                if (birthDate > today) {
                    showFieldError(input, "La date de naissance ne peut pas être dans le futur.");
                    return false;
                }

                // Calcul de l'âge
                let age = today.getFullYear() - birthYear;
                const monthDiff = today.getMonth() - birthMonth;
                if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDay)) {
                    age--;
                }

                if (age < 10) {
                    showFieldError(input, "L'utilisateur doit avoir au moins 10 ans.");
                    return false;
                }
                if (age > 120) {
                    showFieldError(input, "Veuillez entrer une date de naissance réaliste.");
                    return false;
                }
            }
            clearFieldError(input);
            return true;
        }

        function validateSexe() {
            const input = fields.sexe;
            if (!input) return true;
            const val = input.value;

            if (!val || (val !== 'homme' && val !== 'femme')) {
                showFieldError(input, "Veuillez sélectionner le sexe.");
                return false;
            }

            clearFieldError(input);
            return true;
        }

        function validateRole() {
            const input = fields.role;
            if (!input) return true;
            const val = input.value;

            if (!val) {
                showFieldError(input, "Veuillez sélectionner un rôle.");
                return false;
            }

            clearFieldError(input);
            return true;
        }

        function validateStatut() {
            const input = fields.statut;
            if (!input) return true;
            const val = input.value;

            if (!val) {
                showFieldError(input, "Veuillez sélectionner un statut.");
                return false;
            }

            clearFieldError(input);
            return true;
        }

        function validateDateNomination() {
            const input = fields.dateNomination;
            const role = fields.role ? fields.role.value : '';

            // Si le rôle n'est pas admin ou si le champ est masqué, ne pas bloquer
            if (role !== 'admin' || !isFieldVisible(input)) {
                if (input) resetFieldStyle(input);
                return true;
            }

            const val = input.value;
            if (val) {
                const parts = val.split('-');
                if (parts.length === 3) {
                    const nomDate = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
                    const today = new Date();
                    today.setHours(0, 0, 0, 0);

                    // En création, ne peut être antérieure à la date du jour
                    if (!isEditMode && nomDate < today) {
                        showFieldError(input, "La date de nomination ne peut pas être antérieure à la date actuelle.");
                        return false;
                    }
                }
                clearFieldError(input);
            } else {
                resetFieldStyle(input);
            }
            return true;
        }

        function validateSpecialite() {
            const input = fields.specialite;
            const role = fields.role ? fields.role.value : '';

            if (role !== 'apiculteur' || !isFieldVisible(input)) {
                if (input) resetFieldStyle(input);
                return true;
            }

            const val = input.value.trim();
            if (val) {
                if (val.length < 3) {
                    showFieldError(input, "La spécialité doit comporter au moins 3 caractères.");
                    return false;
                }
                clearFieldError(input);
            } else {
                resetFieldStyle(input);
            }
            return true;
        }

        function validateNiveauExperience() {
            const input = fields.niveauExperience;
            const role = fields.role ? fields.role.value : '';

            if (role !== 'responsable' || !isFieldVisible(input)) {
                if (input) resetFieldStyle(input);
                return true;
            }

            clearFieldError(input);
            return true;
        }

        // ==========================================
        // ATTACHEMENT DES ÉVÉNEMENTS EN DIRECT
        // ==========================================

        const listeners = [
            { el: fields.username, fn: validateUsername },
            { el: fields.email, fn: validateEmail },
            { el: fields.firstName, fn: validateFirstName },
            { el: fields.lastName, fn: validateLastName },
            { el: fields.telephone, fn: validateTelephone },
            { el: fields.dateNaissance, fn: validateDateNaissance },
            { el: fields.sexe, fn: validateSexe },
            { el: fields.role, fn: () => {
                validateRole();
                setTimeout(() => {
                    validateDateNomination();
                    validateSpecialite();
                    validateNiveauExperience();
                }, 50);
            }},
            { el: fields.statut, fn: validateStatut },
            { el: fields.dateNomination, fn: validateDateNomination },
            { el: fields.specialite, fn: validateSpecialite },
            { el: fields.niveauExperience, fn: validateNiveauExperience }
        ];

        listeners.forEach(({ el, fn }) => {
            if (!el) return;

            // Validation dès qu'on quitte le champ
            el.addEventListener('blur', fn);

            // Re-validation pendant la frappe (pour corriger les erreurs rapidement)
            const eventName = el.tagName === 'SELECT' ? 'change' : 'input';
            el.addEventListener(eventName, () => {
                const errorEl = getErrorElement(el);
                if (errorEl && errorEl.style.display !== 'none') {
                    fn();
                }
            });
        });

        // ==========================================
        // VALIDATION GLOBALE À LA SOUMISSION
        // ==========================================

        let isSubmitting = false;

        form.addEventListener('submit', function (e) {
            if (isSubmitting) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }

            const checks = [
                validateUsername(),
                validateEmail(),
                validateFirstName(),
                validateLastName(),
                validateTelephone(),
                validateDateNaissance(),
                validateSexe(),
                validateRole(),
                validateStatut(),
                validateDateNomination(),
                validateSpecialite(),
                validateNiveauExperience()
            ];

            const isValid = checks.every(Boolean);

            if (!isValid) {
                e.preventDefault();
                e.stopPropagation();
                isSubmitting = false;

                // Chercher le premier champ en erreur
                const firstErrorField = form.querySelector('input[style*="rgb(220, 53, 69)"], select[style*="rgb(220, 53, 69)"]') ||
                                        form.querySelector('.bf-field-error[style*="display: block"]');

                if (firstErrorField) {
                    const inputToFocus = firstErrorField.tagName === 'DIV'
                        ? firstErrorField.parentElement.querySelector('input, select')
                        : firstErrorField;

                    if (inputToFocus && typeof inputToFocus.focus === 'function') {
                        inputToFocus.focus();
                    }
                    if (inputToFocus && typeof inputToFocus.scrollIntoView === 'function') {
                        inputToFocus.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
                return;
            }

            // Empêcher les doubles envois (spam de clics) et bloquer les boutons
            isSubmitting = true;

            const actionsPanel = document.querySelector('.user-form-actions');
            if (actionsPanel) {
                actionsPanel.style.pointerEvents = 'none';
            }

            const formId = form.getAttribute('id');
            const submitButtons = document.querySelectorAll(
                formId
                    ? `button[type="submit"][form="${formId}"], #${formId} button[type="submit"]`
                    : 'button[type="submit"]'
            );

            // Désactivation visuelle des boutons sans couper les données POST du bouton cliqué
            setTimeout(function () {
                submitButtons.forEach(function (btn) {
                    btn.disabled = true;
                    btn.style.cursor = 'wait';
                });
            }, 0);
        });

        // Réactiver les boutons si la page est restaurée depuis le cache navigateur (bouton Précédent)
        window.addEventListener('pageshow', function () {
            isSubmitting = false;
            const actionsPanel = document.querySelector('.user-form-actions');
            if (actionsPanel) {
                actionsPanel.style.pointerEvents = '';
            }
            const formId = form.getAttribute('id');
            const submitButtons = document.querySelectorAll(
                formId
                    ? `button[type="submit"][form="${formId}"], #${formId} button[type="submit"]`
                    : 'button[type="submit"]'
            );
            submitButtons.forEach(function (btn) {
                btn.disabled = false;
                btn.style.cursor = '';
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initUserFormValidation);
    } else {
        initUserFormValidation();
    }
})();
