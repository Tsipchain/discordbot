LOCALES = {
    "GR": {
        "welcome": "Καλώς ήρθατε στο Thronos Chain!",
        "roadmap_desc": "Εδώ είναι ο οδικός χάρτης του Thronos.",
        "whitepaper_desc": "Εδώ είναι η λευκή βίβλος του Thronos.",
        "website_desc": "Επισκεφθείτε την ιστοσελίδα μας:",
        "verify_btn": "Επαλήθευση",
        "verified_msg": "Επαληθευτήκατε επιτυχώς! Καλώς ήρθατε Thronidian.",
        "lang_selected": "Η γλώσσα ορίστηκε σε: Ελληνικά",
        "verification_title": "Επαλήθευση / Verification",
        "verification_desc": "Κάντε κλικ στο παρακάτω κουμπί για να επαληθευτείτε και να αποκτήσετε πρόσβαση στον διακομιστή.\nClick the button below to verify yourself and gain access to the server.",
        "already_verified": "Είστε ήδη επαληθευμένοι!",
        "role_created": "Ο ρόλος 'Thronidian' δημιουργήθηκε.",
        "role_error": "Αποτυχία ανάθεσης ρόλου."
    },
    "EN": {
        "welcome": "Welcome to Thronos Chain!",
        "roadmap_desc": "Here is the Thronos Roadmap.",
        "whitepaper_desc": "Here is the Thronos Whitepaper.",
        "website_desc": "Visit our website:",
        "verify_btn": "Verify",
        "verified_msg": "Successfully verified! Welcome Thronidian.",
        "lang_selected": "Language set to: English",
        "verification_title": "Verification / Επαλήθευση",
        "verification_desc": "Click the button below to verify yourself and gain access to the server.\nΚάντε κλικ στο παρακάτω κουμπί για να επαληθευτείτε και να αποκτήσετε πρόσβαση στον διακομιστή.",
        "already_verified": "You are already verified!",
        "role_created": "Role 'Thronidian' created successfully.",
        "role_error": "Failed to assign role."
    },
    "ES": {
        "welcome": "¡Bienvenido a Thronos Chain!",
        "roadmap_desc": "Aquí está la hoja de ruta de Thronos.",
        "whitepaper_desc": "Aquí está el libro blanco de Thronos.",
        "website_desc": "Visita nuestro sitio web:",
        "verify_btn": "Verificar",
        "verified_msg": "¡Verificado con éxito! Bienvenido Thronidian.",
        "lang_selected": "Idioma establecido en: Español",
        "verification_title": "Verificación / Verification",
        "verification_desc": "Haga clic en el botón de abajo para verificarse y obtener acceso al servidor.\nClick the button below to verify yourself and gain access to the server.",
        "already_verified": "¡Ya estás verificado!",
        "role_created": "Rol 'Thronidian' creado exitosamente.",
        "role_error": "Error al asignar rol."
    },
    "RU": {
        "welcome": "Добро пожаловать в Thronos Chain!",
        "roadmap_desc": "Вот дорожная карта Thronos.",
        "whitepaper_desc": "Вот белая книга Thronos.",
        "website_desc": "Посетите наш сайт:",
        "verify_btn": "Подтвердить",
        "verified_msg": "Успешно проверено! Добро пожаловать, Thronidian.",
        "lang_selected": "Язык установлен на: Русский",
        "verification_title": "Проверка / Verification",
        "verification_desc": "Нажмите кнопку ниже, чтобы пройти проверку и получить доступ к серверу.\nClick the button below to verify yourself and gain access to the server.",
        "already_verified": "Вы уже проверены!",
        "role_created": "Роль 'Thronidian' успешно создана.",
        "role_error": "Не удалось назначить роль."
    },
    "JA": {
        "welcome": "Thronos Chainへようこそ！",
        "roadmap_desc": "これがThronosのロードマップです。",
        "whitepaper_desc": "これがThronosのホワイトペーパーです。",
        "website_desc": "ウェブサイトをご覧ください：",
        "verify_btn": "確認",
        "verified_msg": "確認が完了しました！Thronidianへようこそ。",
        "lang_selected": "言語が設定されました：日本語",
        "verification_title": "認証 / Verification",
        "verification_desc": "サーバーへのアクセス権を取得するには、下のボタンをクリックしてください。\nClick the button below to verify yourself and gain access to the server.",
        "already_verified": "既に認証されています！",
        "role_created": "ロール 'Thronidian' が作成されました。",
        "role_error": "ロールの割り当てに失敗しました。"
    }
}

DEFAULT_LOCALE = "GR"

def get_text(key, lang_code=None):
    if not lang_code or lang_code not in LOCALES:
        lang_code = DEFAULT_LOCALE
    return LOCALES[lang_code].get(key, key)
