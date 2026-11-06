import { reactive } from 'vue'
import { translateChatText } from './utils/chatTranslations.js'

const ru = {
  'Search by SKU, order#, supplier, trip...': 'Поиск по артикулу, заказу, поставщику, поездке...',
  'Add at least one position before sending the order.': 'Добавьте хотя бы одну позицию перед отправкой заказа.',
  'Save changes before sending the order.': 'Сохраните изменения перед отправкой заказа.',

  'Samples and trips': 'Образцы и поездки',
  'New sample order': 'Новый заказ образцов', 'Edit sample order': 'Заказ образцов',
  'Trip / exhibition / meeting': 'Поездка / выставка / место встречи',
  'Filter by trip or exhibition...': 'Поиск по поездке или выставке...',
  'For example: Guangzhou exhibition': 'Например: выставка Гуанчжоу',
  'Optional. You can save an order with only a supplier.': 'Необязательно. Для сохранения заказа достаточно поставщика.',
  'Additional details': 'Дополнительные сведения',

  'Other': 'Другое', 'Comment': 'Комментарий', 'Write-off report': 'Отчёт по списаниям',
  'Unable to add department.': 'Не удалось добавить отдел.',
  'Departments': 'Отделы', 'No department': 'Без отдела',
  'Archive department': 'Архивировать отдел', 'Restore department': 'Восстановить отдел',
  'Department has been added.': 'Отдел добавлен.', 'Department has been saved.': 'Отдел сохранён.',
  'Department has been archived.': 'Отдел архивирован.', 'Department has been restored.': 'Отдел восстановлен.',
  'Unable to update department.': 'Не удалось обновить отдел.',
  'Expand employee details': 'Раскрыть карточку сотрудника', 'Collapse employee details': 'Свернуть карточку сотрудника',
  'Expires at': 'Действует до', 'Resend invitation': 'Отправить приглашение повторно',
  'Revoke invitation': 'Отозвать приглашение', 'Invitation has been resent.': 'Приглашение отправлено повторно.',
  'Invitation has been revoked.': 'Приглашение отозвано.', 'Unable to update invitation.': 'Не удалось обновить приглашение.',
  'Unable to send invitation email. Please try again.': 'Не удалось отправить письмо с приглашением. Попробуйте ещё раз.',
  'Invitation is invalid or expired.': 'Приглашение недействительно или срок его действия истёк.',
  'A department with this name already exists.': 'Отдел с таким названием уже существует.',
  'Use Russian and English names.': 'Укажите названия на русском и английском.',
  'Department names must be at most 150 characters.': 'Название отдела не должно превышать 150 символов.',
  'Department is not available for your company.': 'Этот отдел недоступен для вашей компании.',

  'Supplier Orders': 'Заказы поставщикам', 'Customer Orders': 'Заказы покупателей',
  'Products': 'Товары', 'Warehouse': 'Склад', 'Counterparties': 'Контрагенты', 'Profile': 'Профиль',
  'Login': 'Войти', 'Register': 'Регистрация', 'Email': 'Электронная почта', 'Password': 'Пароль',
  'Confirm Password': 'Повторите пароль', 'Confirm password': 'Повторите пароль', 'Username': 'Имя пользователя',
  'Forgot password?': 'Забыли пароль?', 'Forgot Password': 'Восстановление пароля',
  'Reset Password': 'Сбросить пароль', 'Send Reset Code': 'Отправить код', 'Reset Code': 'Код сброса',
  'New Password': 'Новый пароль', 'Verify Your Email': 'Подтверждение почты', 'Verification Code': 'Код подтверждения',
  'Verify': 'Подтвердить', 'Company Name': 'Название компании', 'Country of business': 'Страна ведения бизнеса',
  'Interface language': 'Язык интерфейса', 'Company language': 'Язык компании', 'Russian': 'Русский', 'English': 'Английский',
  'Status': 'Статус', 'Actions': 'Действия', 'Name': 'Название', 'SKU': 'Артикул', 'Supplier': 'Поставщик',
  'Customer': 'Покупатель', 'Category': 'Категория', 'Unit': 'Единица', 'Quantity unit': 'Единица измерения',
  'Categories': 'Категории', 'Units': 'Единицы измерения', 'Color': 'Цвет', 'Description': 'Описание',
  'Available': 'Доступно', 'Expected': 'Ожидается', 'Minimum': 'Минимум', 'Minimum stock': 'Минимальный остаток',
  'Monthly use': 'Расход в месяц', 'Average consumption per month': 'Средний расход в месяц',
  'Average monthly consumption': 'Средний расход в месяц',
  'Purchase batch': 'Закупочная партия', 'Projected': 'Прогнозный остаток',
  'Recommended order': 'Рекомендуемый заказ', 'Deficit at delivery': 'Дефицит к поставке',
  'Forecast': 'Прогноз', 'Manual': 'Ручной', 'Automatic from shipments': 'Автоматически по отгрузкам',
  'Normal': 'Норма', 'Out of stock': 'Нет в наличии', 'Below minimum': 'Ниже минимума',
  'Order required': 'Требуется заказ', 'Incoming covers demand': 'Поставка покрывает потребность',
  'No forecast': 'Нет прогноза', 'No forecast data': 'Нет данных для прогноза',
  'Requires attention': 'Требуют внимания', 'Attention': 'Внимание',
  'Add Counterparty': 'Добавить контрагента', 'Create customer': 'Создать покупателя', 'Create supplier': 'Создать поставщика',
  'Counterparty': 'Контрагент', 'Unique Code': 'Уникальный код', 'Region': 'Регион', 'Phone': 'Телефон',
  'Address': 'Адрес', 'Type or select': 'Введите или выберите', 'Chinese': 'Китайский', 'Local': 'Местный',
  'All': 'Все', 'Active': 'Активные', 'Archived': 'Архивные', 'Archive': 'В архив', 'Restore': 'Восстановить', 'Restored': 'Восстановлен',
  'Delete': 'Удалить', 'Delete permanently': 'Удалить навсегда', 'Clear': 'Очистить', 'Cancel': 'Отмена',
  'Close': 'Закрыть', 'Reset': 'Сбросить', 'Save': 'Сохранить', 'Edit': 'Изменить', 'Add': 'Добавить',
  'Create new item': 'Создать новое значение', 'Creating new item': 'Создание нового значения',
  'Editing selected item': 'Редактирование выбранного значения', 'Add new item': 'Добавить новое значение',
  'Save changes': 'Сохранить изменения',
  'Russian name': 'Название на русском', 'English name': 'Название на английском',
  'Delete selected item': 'Удалить выбранное значение',
  'Remove position': 'Удалить позицию', 'Delete attachment': 'Удалить вложение',
  'Loading...': 'Загрузка...', 'Loading settings...': 'Загрузка настроек...', 'Loading employees...': 'Загрузка сотрудников...',
  'Loading stock control...': 'Загрузка контроля остатков...', 'No orders yet.': 'Заказов пока нет.',
  'No positions yet.': 'Позиций пока нет.', 'No products found.': 'Товары не найдены.',
  'No counterparties yet.': 'Контрагентов пока нет.', 'No warehouse items found.': 'Складские позиции не найдены.',
  'No warehouse control data is available.': 'Данные контроля остатков отсутствуют.',
  'No warehouse products have a minimum stock configured.': 'Нет складских товаров с настроенным минимальным остатком.',
  'Search by name or SKU...': 'Поиск по названию или артикулу...',
  'Find product by name or SKU...': 'Найти товар по названию или артикулу...',
  'Search warehouse items...': 'Поиск по складу...', 'Search by name/code/email...': 'Поиск по названию, коду или почте...',
  'Search by SKU, order#, supplier, track...': 'Поиск по артикулу, заказу, поставщику или треку...',
  'Search by order#, customer, track...': 'Поиск по заказу, покупателю или треку...',
  'Select...': 'Выберите...', 'Select supplier...': 'Выберите поставщика...', 'Select customer...': 'Выберите покупателя...',
  'Select category...': 'Выберите категорию...', 'Select unit...': 'Выберите единицу...', 'Select status...': 'Выберите статус...',
  'Filter by category...': 'Фильтр по категории...', 'Filter by supplier...': 'Фильтр по поставщику...',
  'Category...': 'Категория...', 'Supplier...': 'Поставщик...', 'Customer...': 'Покупатель...',
  'All stock statuses': 'Все состояния остатков', 'Only available': 'Только в наличии',
  'Order': 'Заказ', 'Order#': 'Заказ №', 'Order Number': 'Номер заказа', 'Date': 'Дата', 'Qty': 'Количество',
  'Total': 'Итого', 'Subtotal': 'Подытог', 'Currency': 'Валюта', 'Amount CNY': 'Сумма, CNY', 'CNY': 'CNY',
  'Sent': 'Отправлено', 'Shipment': 'Отгрузка', 'Delivery': 'Доставка', 'Track Number': 'Трек-номер',
  'Shipping Address': 'Адрес доставки', 'Shipping Code': 'Код доставки', 'Payment Date': 'Дата оплаты',
  'Customer Comment': 'Комментарий покупателя', 'Supplier Comment': 'Комментарий поставщика',
  'Internal Comment': 'Внутренний комментарий', 'Positions': 'Позиции', 'Attachments': 'Вложения', 'Files': 'Файлы',
  'Related documents': 'Связанные документы', 'Change History': 'История изменений',
  'Product Change History': 'История изменений товара', 'Created At:': 'Создано:', 'Created By:': 'Создал:',
  'Updated At:': 'Обновлено:', 'Updated By:': 'Обновил:', 'Field': 'Поле',
  'Purchase Price': 'Закупочная цена', 'Purchase price': 'Закупочная цена', 'Sale Price': 'Цена продажи',
  'Sale price': 'Цена продажи', 'Purchase / Sale Price': 'Цена закупки / продажи',
  'Purchase / Cost / Sale': 'Закупка / себестоимость / продажа', 'Cost price': 'Себестоимость',
  'Sale price calculation': 'Расчёт цены продажи', 'Automatic': 'Автоматический',
  'Automatic price for comparison': 'Автоматическая цена для сравнения',
  'Only a company administrator can set a manual sale price.': 'Ручную цену продажи может устанавливать только администратор компании.',
  'Only a company administrator can change the sale price.': 'Изменять цену продажи может только администратор компании.',
  'Clear the price to calculate it automatically.': 'Очистите поле, чтобы рассчитать цену автоматически.',
  'Markup, %': 'Наценка, %', 'Applied markup': 'Применённая наценка',
  'product category': 'категория товара', 'company settings': 'настройки компании',
  'Defective': 'Брак', 'Physical stock': 'Физический остаток', 'Operations': 'Операции',
  'Manage stock': 'Операции', 'Warehouse operation': 'Операция со складом', 'Operation': 'Операция',
  'Return defect to available stock': 'Вернуть брак в доступный остаток',
  'Write off unusable defect': 'Списать непригодный брак',
  'Write off available stock': 'Списать доступный товар',
  'Reason': 'Причина', 'Marketing and internal use': 'Маркетинг и внутреннее использование',
  'Damage during storage': 'Повреждение при хранении', 'Inventory adjustment': 'Корректировка после инвентаризации',
  'Enter a positive quantity.': 'Введите количество больше нуля.',
  'Select a write-off reason.': 'Выберите причину списания.',
  'Unable to save warehouse operation.': 'Не удалось сохранить складскую операцию.',
  'Sale price cannot be negative.': 'Цена продажи не может быть отрицательной.',
  'Calculated from purchase price, exchange rates, logistics, internal costs and packaging.': 'Рассчитывается из закупочной цены, курсов валют, логистики, внутренних расходов и упаковки.',
  'Weight per unit is empty. Cost and automatic sale price will remain zero. Continue?': 'Вес единицы не указан. Себестоимость и автоматическая цена продажи останутся нулевыми. Продолжить?',
  'Discount, %': 'Скидка, %', 'Discount amount': 'Сумма скидки', 'Order discount, %': 'Скидка заказа, %',
  'Defect qty': 'Количество брака', 'Weight per unit, kg': 'Вес единицы, кг',
  'Warehouse analytics': 'Аналитика склада', 'Warehouse product comparison': 'Сравнение складских товаров',
  'Warehouse analytics metric': 'Показатель аналитики склада', 'Warehouse stock control': 'Контроль складских остатков',
  'Download Excel': 'Скачать Excel', 'Export': 'Экспорт', 'Open summary': 'Открыть сводку', 'Open warehouse': 'Открыть склад',
  'Check company settings': 'Проверьте настройки компании', 'Open settings': 'Открыть настройки', 'Later': 'Позже',
  'Company settings': 'Настройки компании', 'Company details for documents': 'Реквизиты компании для документов',
  'Company logo': 'Логотип компании', 'Company phone': 'Телефон компании', 'Company address': 'Адрес компании',
  'China warehouse address': 'Адрес склада в Китае', 'Bank details': 'Банковские реквизиты',
  'Pricing settings': 'Настройки ценообразования', 'CNY to local rate': 'Курс CNY к местной валюте',
  'USD to local rate': 'Курс USD к местной валюте', 'Logistics USD/kg': 'Логистика, USD/кг',
  'Internal logistics, %': 'Внутренняя логистика, %', 'Retail tax, %': 'Налог с продажи, %',
  'Acquiring fee, %': 'Эквайринг, %', 'Packaging fee, %': 'Упаковка, %', 'Margin, %': 'Маржа, %',
  'Average delivery lead, calendar days': 'Средний срок поставки, календарных дней',
  'Company time zone': 'Часовой пояс компании', 'Weekly warehouse stock notification': 'Еженедельное уведомление по остаткам',
  'Notification day': 'День уведомления', 'Notification time': 'Время уведомления',
  'Automatic consumption history': 'История для автоматического расхода',
  '30 days': '30 дней', '7 days': '7 дней', '30 days — reacts faster': '30 дней — быстрее реагирует',
  '90 days — recommended': '90 дней — рекомендуется', '180 days — more stable': '180 дней — стабильнее',
  'Monday': 'Понедельник', 'Tuesday': 'Вторник', 'Wednesday': 'Среда', 'Thursday': 'Четверг',
  'Friday': 'Пятница', 'Saturday': 'Суббота', 'Sunday': 'Воскресенье',
  'Profile details': 'Данные профиля', 'Edit profile': 'Редактировать профиль',
  'Update your contact information and photo': 'Обновите контактные данные и фотографию',
  'First name': 'Имя', 'Last name': 'Фамилия', 'Middle name': 'Отчество', 'Mobile phone': 'Мобильный телефон',
  'Work email': 'Рабочая почта', 'Personal email': 'Личная почта', 'Position': 'Должность',
  'Department': 'Отдел', 'Birth date': 'Дата рождения', 'Hire date': 'Дата приёма',
  'not filled': 'не указано',
  'Notification language': 'Язык интерфейса', 'Active company': 'Текущая компания',
  'Invite employee': 'Пригласить сотрудника', 'Employees': 'Сотрудники', 'Employee email': 'Почта сотрудника',
  'Access role': 'Роль доступа', 'Role': 'Роль', 'Roles': 'Роли', 'Admin': 'Администратор',
  'Manager': 'Менеджер', 'Viewer': 'Наблюдатель', 'Pending invitations': 'Ожидающие приглашения',
  'admin': 'Администратор', 'manager': 'Менеджер', 'viewer': 'Наблюдатель',
  'active': 'Активен', 'disabled': 'Уволен', 'pending': 'Ожидает', 'Company admin': 'Администратор компании',
  'Accept invitation': 'Принять приглашение', 'Go to login': 'Перейти ко входу',
  'Notifications': 'Уведомления', 'Mark all as read': 'Прочитать все', 'No notifications': 'Уведомлений нет',
  'Stored for 30 days': 'Хранятся 30 дней', 'Hide notification': 'Скрыть уведомление',
  'New': 'Новое', 'Resolved': 'Решено', 'Today': 'Сегодня', 'Open': 'Открыть',
  'In progress': 'В работе', 'Shipped': 'Отгружено', 'Completed': 'Завершено',
  'Cancelled': 'Отменено', 'In production': 'В производстве', 'In transit': 'В пути',
  'Received': 'Получено', 'Blocked': 'Заблокировано', 'General': 'Общая',
  'pcs': 'шт.', 'Pieces': 'Штуки', 'kg': 'кг', 'Kilograms': 'Килограммы', 'g': 'г', 'Grams': 'Граммы',
  'm': 'м', 'Meters': 'Метры', 'm2': 'м²', 'Square meters': 'Квадратные метры',
  'm3': 'м³', 'Cubic meters': 'Кубические метры', 'box': 'кор.', 'Boxes': 'Коробки', 'set': 'компл.', 'Sets': 'Комплекты',
  'directory.category.General': 'Общая',
  'directory.unit.pcs': 'шт.', 'directory.unit.kg': 'кг', 'directory.unit.g': 'г', 'directory.unit.m': 'м',
  'directory.unit.m2': 'м²', 'directory.unit.m3': 'м³', 'directory.unit.box': 'кор.', 'directory.unit.set': 'компл.',
  'directory.counterpartyStatus.New': 'Новый', 'directory.counterpartyStatus.Active': 'Активный',
  'directory.counterpartyStatus.Blocked': 'Заблокирован',
  'directory.customerOrderStatus.New': 'Новый', 'directory.customerOrderStatus.In progress': 'В работе',
  'directory.customerOrderStatus.Shipped': 'Отгружен', 'directory.customerOrderStatus.Completed': 'Завершён',
  'directory.customerOrderStatus.Cancelled': 'Отменён',
  'directory.supplierOrderStatus.New': 'Новый', 'directory.supplierOrderStatus.In production': 'В производстве',
  'directory.supplierOrderStatus.In transit': 'В пути', 'directory.supplierOrderStatus.Received': 'Получен',
  'directory.supplierOrderStatus.Cancelled': 'Отменён',
  'role.Company admin': 'Администратор компании', 'role.WED manager': 'Менеджер ВЭД',
  'role.Sales manager': 'Менеджер продаж', 'role.Financial analyst': 'Финансовый аналитик',
  'role.Warehouse manager': 'Менеджер склада', 'role.Viewer': 'Наблюдатель',
  'Unable to update employee role.': 'Не удалось изменить роль сотрудника.',
  'Top 10': 'Топ-10', 'Top 20': 'Топ-20', 'Top 30': 'Топ-30', 'Ranking size': 'Размер рейтинга',
  'Supplier analytics': 'Аналитика поставщиков', 'Customer analytics': 'Аналитика покупателей',
  'Quick report periods': 'Быстрый выбор периода', 'This month': 'Этот месяц', 'From': 'С', 'To': 'По',
  'Toggle navigation': 'Открыть меню', '← Back to Orders': '← Назад к заказам',
  '+ Add Counterparty': '+ Добавить контрагента', '+ Add Order': '+ Добавить заказ',
  '+ Add Product': '+ Добавить товар', 'Apply': 'Применить', 'Next': 'Далее', 'Previous': 'Назад',
  'Export orders': 'Экспорт заказов', 'Invite': 'Пригласить', 'Change photo': 'Изменить фото',
  'Image': 'Изображение', 'Image Preview': 'Предпросмотр изображения', 'Code': 'Код',
  'Contact information': 'Контактные данные', 'Directories': 'Справочники', 'Employee profile': 'Профиль сотрудника',
  'Quantity': 'Количество', 'Reason': 'Причина', 'Source': 'Источник', 'Symbol': 'Символ',
  'System role': 'Системная роль', 'User': 'Пользователь', 'Warehouse item': 'Складская позиция',
  'China Exit Date': 'Дата отправки из Китая', 'Production Due': 'Срок производства',
  'Plan Receipt': 'Плановое поступление', 'Logistic Invoice#': 'Счёт логистики №',
  'QR': 'QR', 'QR Code': 'QR-код', 'QR Code Image': 'Изображение QR-кода', 'Payment QR': 'QR для оплаты',
  'Stock control': 'Контроль остатков', 'Consumption calculation': 'Расчёт расхода',
  'Automatic mode uses the history period configured for the company.': 'Автоматический режим использует период истории, заданный для компании.',
  'Each warehouse product can use a manual monthly value or an automatic value calculated from actual shipments.': 'Для каждого складского товара можно задать расход вручную или рассчитывать его автоматически по фактическим отгрузкам.',
  'The quantity that should remain available in the warehouse.': 'Количество товара, которое должно оставаться доступным на складе.',
  'Used to forecast the balance by the next delivery.': 'Используется для прогноза остатка к следующей поставке.',
  'Roll, box, or supplier lot used to round the suggested order.': 'Рулон, коробка или партия поставщика, до которой округляется рекомендуемый заказ.',
  'The notification is created on the first app activity after this time.': 'Уведомление создаётся при первом открытии приложения после указанного времени.',
  'Blank dates mean all time. Cancelled orders are excluded. Search and status filters on the page do not affect this report.': 'Пустые даты означают весь период. Отменённые заказы не учитываются. Поиск и фильтр статуса на странице на этот отчёт не влияют.',
  'Archived product is read-only. Restore it before editing.': 'Архивный товар доступен только для просмотра. Восстановите его перед редактированием.',
  'Remove discounts from product lines before setting an order discount.': 'Перед установкой скидки на заказ уберите скидки у отдельных позиций.',
  'Remove the order discount before setting discounts on product lines.': 'Перед установкой скидок на позиции уберите общую скидку заказа.',
  'Changing country updates the company currency, exchange rates, and default tax rate.': 'При смене страны обновятся валюта компании, курсы и ставка налога по умолчанию.',
  'We use this to set the default currency, tax rate, and exchange rates.': 'По стране настраиваются валюта, налоговая ставка и курсы валют по умолчанию.',
  'Thanks for using ChinaTradeERP. We filled the basic company settings from your business country.': 'Спасибо, что используете ChinaTradeERP. Основные настройки компании заполнены на основе выбранной страны.',
  'Please check exchange rates, tax rate, and pricing settings so orders and product prices are calculated correctly.': 'Проверьте курсы валют, налог и настройки цен, чтобы суммы заказов и цены товаров рассчитывались правильно.',
  'At least 8 characters, one uppercase letter and one number.': 'Не менее 8 символов, одна заглавная буква и одна цифра.',
  'Enter the 6-digit code sent to your email': 'Введите шестизначный код из письма',
  'Company name is required and must be unique.': 'Название компании обязательно и должно быть уникальным.',
  'Country of business is required.': 'Укажите страну ведения бизнеса.', 'Password is required.': 'Введите пароль.',
  'Username is required.': 'Введите имя пользователя.', 'Valid email is required.': 'Введите корректный адрес электронной почты.',
  'Passwords do not match.': 'Пароли не совпадают.',
  'An existing account can be invited to another company.': 'Существующий аккаунт можно пригласить в другую компанию.',
  'This email already has an account. Sign in first, then open this invitation again.': 'Для этой почты уже есть аккаунт. Сначала войдите, затем снова откройте приглашение.',
  'You can accept this invitation with your existing account.': 'Вы можете принять это приглашение через существующий аккаунт.',
  'Add an employee to': 'Добавить сотрудника в', 'Select region...': 'Выберите регион...',
  'Select role...': 'Выберите роль...', 'Selected:': 'Выбрано:', 'Selection changed': 'Выбор изменён',
  'No changes found.': 'Изменений нет.', 'No data for the selected filters.': 'По выбранным фильтрам данных нет.',
  'Unspecified': 'Не указано', 'Selected products': 'Выбрано товаров', 'Top': 'Топ', 'of': 'из', 'Value': 'Значение',
  'days': 'дн.',
  'No employees in this list.': 'В этом списке нет сотрудников.', 'No pending invitations.': 'Нет ожидающих приглашений.',
  'No matches': 'Совпадений нет', 'No status': 'Без статуса', 'Parent customer order is not linked.': 'Связанный заказ покупателя не указан.',
  'Loading analytics...': 'Загрузка аналитики...', 'Loading invitation...': 'Загрузка приглашения...',
  'Dismiss': 'Уволить', 'Dismissed': 'Уволен', 'Dismissed at': 'Дата увольнения',
  'Active employees': 'Активные', 'Dismissed employees': 'Уволенные', 'Dismissed on': 'Уволен',
  'Dismiss employee': 'Уволить сотрудника', 'from company': 'из компании', 'this company': 'этой компании',
  'Reason': 'Причина',
  'Drag photo, use mouse wheel to zoom': 'Перетаскивайте фото, масштабируйте колёсиком мыши',
  'Order date from': 'Дата заказа с', 'Pricing settings for': 'Настройки цен для', 'Product': 'Товар',
  'by': 'от', 'invited': 'приглашён',
  'Archived': 'В архиве', 'Updated': 'Обновлено', 'delivery lead': 'срок поставки',
  'calendar days': 'календарных дней', 'your company': 'вашу компанию',
  '1 year': '1 год', '6 months': '6 месяцев', 'All customers': 'Все покупатели', 'All suppliers': 'Все поставщики',
  'All time': 'За всё время', 'Automatic value': 'Автоматическое значение', 'Manual value': 'Ручное значение',
  'Preliminary automatic value': 'Предварительное автоматическое значение', 'Insufficient history': 'Недостаточно истории',
  'Not configured': 'Не настроено', 'CNY amount': 'Сумма в CNY', 'Local amount': 'Сумма в местной валюте',
  'Total, CNY': 'Итого, CNY', 'Total, local': 'Итого в местной валюте',
  'Item purchase price, CNY': 'Закупочная цена позиции, CNY', 'Item sale price': 'Цена продажи позиции',
  'Add Customer': 'Добавить покупателя', 'Add Supplier': 'Добавить поставщика', 'Add Product': 'Добавить товар',
  'Create Order': 'Создать заказ', 'New Order': 'Новый заказ', 'Edit Order': 'Изменить заказ',
  'Update Order': 'Обновить заказ', 'Create supplier orders': 'Создать заказы поставщикам',
  'Update supplier orders': 'Обновить заказы поставщикам', 'Customer order': 'Заказ покупателя',
  'Supplier order': 'Заказ поставщику', 'Customer order status': 'Статус заказа покупателя',
  'Supplier order status': 'Статус заказа поставщику', 'Customer order statuses': 'Статусы заказов покупателей',
  'Supplier order statuses': 'Статусы заказов поставщикам', 'Counterparty status': 'Статус контрагента',
  'Counterparty statuses': 'Статусы контрагентов', 'Customer role': 'Роль покупателя', 'Supplier role': 'Роль поставщика',
  'Customer report': 'Отчёт по покупателям', 'Supplier report': 'Отчёт по поставщикам',
  'Download report': 'Скачать отчёт', 'Downloading...': 'Скачивание...', 'Refreshing...': 'Обновление...',
  'Saving...': 'Сохранение...', 'Sending...': 'Отправка...', 'Creating...': 'Создание...', 'Updating...': 'Обновление...',
  'Accepting...': 'Принятие...', 'Dismissing...': 'Увольнение...', 'Wait...': 'Подождите...',
  'Create account': 'Создать аккаунт', 'Creating account...': 'Создание аккаунта...', 'Logging out...': 'Выход...',
  'Save profile': 'Сохранить профиль', 'Save settings': 'Сохранить настройки', 'Send invitation': 'Отправить приглашение',
  'Send to Customer': 'Отправить покупателю', 'Send to Supplier': 'Отправить поставщику',
  'Restore product purchase price': 'Вернуть закупочную цену товара', 'Restore product sale price': 'Вернуть цену продажи товара',
  'Open QR': 'Открыть QR', 'Product Image': 'Фото товара', 'Profile avatar': 'Фото профиля',
  'Avatar crop preview': 'Предпросмотр фото профиля', 'QR Image': 'Изображение QR', 'QR code': 'QR-код',
  'QR preview': 'Предпросмотр QR', 'Delete selected item': 'Удалить выбранный элемент',
  'New category name': 'Название новой категории', 'New unit name': 'Название новой единицы',
  'No changes to save': 'Нет изменений для сохранения', 'No related documents yet.': 'Связанных документов пока нет.',
  'No related supplier orders.': 'Связанных заказов поставщикам нет.', 'No supplier orders linked yet.': 'Заказы поставщикам пока не связаны.',
  'Company settings have been saved.': 'Настройки компании сохранены.', 'Counterparty saved': 'Контрагент сохранён',
  'Invitation has been sent.': 'Приглашение отправлено.', 'Order created': 'Заказ создан', 'Order saved': 'Заказ сохранён',
  'Order sent': 'Заказ отправлен', 'Product archived': 'Товар перемещён в архив', 'Product deleted': 'Товар удалён',
  'Product restored': 'Товар восстановлен', 'Password updated successfully.': 'Пароль успешно изменён.',
  'Reset code sent to your email.': 'Код сброса отправлен на вашу почту.',
  'Email successfully verified! Redirecting...': 'Почта подтверждена. Переходим дальше...',
  'Please enter SKU': 'Введите артикул', 'Please enter a product name': 'Введите название товара',
  'Please enter counterparty name': 'Введите название контрагента', 'Please select a supplier': 'Выберите поставщика',
  'Please select a country from the list.': 'Выберите страну из списка.',
  'Select at least one role: supplier or customer.': 'Выберите хотя бы одну роль: поставщик или покупатель.',
  'Select supplier before adding positions.': 'Перед добавлением позиций выберите поставщика.',
  'Select a customer before saving the order.': 'Перед сохранением заказа выберите покупателя.',
  'End date must be on or after start date.': 'Дата окончания должна быть не раньше даты начала.',
  'The end date must be on or after the start date.': 'Дата окончания должна быть не раньше даты начала.',
  'Warehouse control quantities must be valid positive values.': 'Значения контроля остатков должны быть корректными положительными числами.',
  'Email not provided.': 'Электронная почта не указана.', 'Password is too weak.': 'Пароль слишком простой.',
  'Something went wrong.': 'Что-то пошло не так.', 'Login failed.': 'Не удалось войти.',
  'Registration failed.': 'Не удалось зарегистрироваться.', 'Verification failed.': 'Не удалось подтвердить почту.',
  'Failed to reset password.': 'Не удалось сбросить пароль.', 'Invitation is invalid or expired.': 'Приглашение недействительно или устарело.',
  'Invitation token is missing.': 'В приглашении отсутствует токен.', 'Unable to accept invitation.': 'Не удалось принять приглашение.',
  'Unable to create counterparty': 'Не удалось создать контрагента', 'Unable to create supplier orders': 'Не удалось создать заказы поставщикам',
  'Unable to delete counterparty.': 'Не удалось удалить контрагента.', 'Unable to delete file.': 'Не удалось удалить файл.',
  'Unable to delete order.': 'Не удалось удалить заказ.', 'Unable to dismiss employee.': 'Не удалось отключить сотрудника.',
  'Unable to download report. Please try again.': 'Не удалось скачать отчёт. Попробуйте ещё раз.',
  'Unable to download warehouse stock control.': 'Не удалось скачать отчёт контроля остатков.',
  'Unable to export orders.': 'Не удалось выгрузить заказы.', 'Unable to export the warehouse report.': 'Не удалось выгрузить складской отчёт.',
  'Unable to load change history.': 'Не удалось загрузить историю изменений.', 'Unable to load company settings.': 'Не удалось загрузить настройки компании.',
  'Unable to load employees.': 'Не удалось загрузить сотрудников.', 'Unable to load order.': 'Не удалось загрузить заказ.',
  'Unable to load orders': 'Не удалось загрузить заказы', 'Unable to load product history.': 'Не удалось загрузить историю товара.',
  'Unable to load product.': 'Не удалось загрузить товар.', 'Unable to load products': 'Не удалось загрузить товары',
  'Unable to load reference data.': 'Не удалось загрузить справочники.', 'Unable to load warehouse analytics.': 'Не удалось загрузить аналитику склада.',
  'Unable to load warehouse stock control.': 'Не удалось загрузить контроль остатков.', 'Unable to load warehouse.': 'Не удалось загрузить склад.',
  'Unable to save company settings.': 'Не удалось сохранить настройки компании.',
  'Unable to save order before adding positions.': 'Не удалось сохранить заказ перед добавлением позиций.',
  'Unable to save order.': 'Не удалось сохранить заказ.', 'Unable to save order. Please check the fields.': 'Не удалось сохранить заказ. Проверьте поля.',
  'Unable to save product': 'Не удалось сохранить товар', 'Unable to save profile': 'Не удалось сохранить профиль',
  'Unable to send invitation.': 'Не удалось отправить приглашение.', 'Unable to send order.': 'Не удалось отправить заказ.',
  'Unable to switch company': 'Не удалось переключить компанию', 'Save error': 'Ошибка сохранения',
  'Delete this counterparty?': 'Удалить этого контрагента?', 'Delete this file?': 'Удалить этот файл?',
  'Delete this order?': 'Удалить этот заказ?', 'Delete this product permanently?': 'Удалить этот товар навсегда?',
  'Move this product to archive?': 'Переместить этот товар в архив?', 'Save changes before leaving?': 'Сохранить изменения перед выходом?',
  'Leave without saving changes?': 'Выйти без сохранения изменений?', 'Send order to customer?': 'Отправить заказ покупателю?',
  'Send order to supplier?': 'Отправить заказ поставщику?',
  'Permanently delete this product? This action cannot be undone.': 'Удалить товар навсегда? Это действие нельзя отменить.',
  'Start typing a country...': 'Начните вводить страну...', 'Supplier order date from': 'Дата заказа поставщику с',
  'Supplier order date to': 'Дата заказа поставщику по',
  'Supplier order date to': 'Дата заказа поставщику по',
}

export const languageState = reactive({
  locale: localStorage.getItem('app_language') || 'ru',
})

const originalText = new WeakMap()
const originalAttributes = new WeakMap()
const lastAppliedText = new WeakMap()
const lastAppliedAttributes = new WeakMap()
let listenersInstalled = false
let scheduled = false

export function t(value) {
  if (languageState.locale !== 'ru') return value
  return ru[value] || value
}

function translatedDynamic(value) {
  const trimmed = value.trim()
  if (ru[trimmed]) return value.replace(trimmed, ru[trimmed])
  let match = trimmed.match(/^Showing (\d+)-(\d+) of (\d+)$/)
  if (match) return value.replace(trimmed, `Показано ${match[1]}–${match[2]} из ${match[3]}`)
  match = trimmed.match(/^Page (\d+) \/ (\d+)$/)
  if (match) return value.replace(trimmed, `Страница ${match[1]} из ${match[2]}`)
  return value
}

function translateElement(root = document.body) {
  if (!root) return
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let node
  while ((node = walker.nextNode())) {
    if (!node.parentElement || ['SCRIPT', 'STYLE'].includes(node.parentElement.tagName)) continue
    if (node.parentElement.closest('[data-i18n-skip]')) continue
    if (!originalText.has(node)) originalText.set(node, node.nodeValue)
    const lastApplied = lastAppliedText.get(node)
    if (lastApplied !== undefined && node.nodeValue !== lastApplied) {
      originalText.set(node, node.nodeValue)
    }
    const source = originalText.get(node)
    const translated = node.parentElement.closest('[data-chat-ui]')
      ? translateChatText(source, languageState.locale)
      : languageState.locale === 'ru' ? translatedDynamic(source) : source
    if (node.nodeValue !== translated) node.nodeValue = translated
    lastAppliedText.set(node, translated)
  }
  const elements = root.querySelectorAll ? [root, ...root.querySelectorAll('[placeholder], [title], [aria-label]')] : []
  elements.forEach(element => {
    if (!(element instanceof Element)) return
    if (element.closest('[data-i18n-skip]') || element.hasAttribute('data-i18n-attributes-skip')) return
    let originals = originalAttributes.get(element)
    if (!originals) {
      originals = {}
      for (const name of ['placeholder', 'title', 'aria-label']) {
        if (element.hasAttribute(name)) originals[name] = element.getAttribute(name)
      }
      originalAttributes.set(element, originals)
    }
    let lastApplied = lastAppliedAttributes.get(element)
    if (!lastApplied) {
      lastApplied = {}
      lastAppliedAttributes.set(element, lastApplied)
    }
    for (const [name, source] of Object.entries(originals)) {
      const current = element.getAttribute(name)
      if (lastApplied[name] !== undefined && current !== lastApplied[name]) {
        originals[name] = current
      }
      const currentSource = originals[name]
      const translated = element.closest('[data-chat-ui]')
        ? translateChatText(currentSource, languageState.locale)
        : languageState.locale === 'ru' ? (ru[currentSource] || currentSource) : currentSource
      if (element.getAttribute(name) !== translated) element.setAttribute(name, translated)
      lastApplied[name] = translated
    }
  })
}

function scheduleTranslation() {
  if (scheduled) return
  scheduled = true
  queueMicrotask(() => {
    scheduled = false
    translateElement()
  })
}

export function refreshTranslations() {
  scheduleTranslation()
}

export function setLanguage(locale) {
  languageState.locale = locale === 'en' ? 'en' : 'ru'
  localStorage.setItem('app_language', languageState.locale)
  scheduleTranslation()
  window.dispatchEvent(new CustomEvent('language-changed', { detail: languageState.locale }))
}

export function installI18n(app) {
  app.config.globalProperties.$t = t
  app.config.globalProperties.$setLanguage = setLanguage
  if (!listenersInstalled) {
    listenersInstalled = true
    document.addEventListener('click', scheduleTranslation)
    document.addEventListener('change', scheduleTranslation)
    window.addEventListener('popstate', scheduleTranslation)
    // Vue renders asynchronous chat updates after the API response interceptor.
    // Observe only chat UI changes, and translate those roots rather than the ERP tables.
    let chatScheduled = false
    const observer = new MutationObserver(changes => {
      const relevant = changes.some(change => {
        const element = change.target.nodeType === 3 ? change.target.parentElement : change.target
        return element?.closest?.('[data-chat-ui]') || [...change.addedNodes].some(node =>
          node.nodeType === 1 && (node.matches('[data-chat-ui]') || node.querySelector('[data-chat-ui]')))
      })
      if (!relevant || chatScheduled) return
      chatScheduled = true
      queueMicrotask(() => {
        chatScheduled = false
        document.querySelectorAll('[data-chat-ui]').forEach(root => {
          if (!root.parentElement?.closest('[data-chat-ui]')) translateElement(root)
        })
      })
    })
    observer.observe(document.body, { subtree: true, childList: true, characterData: true,
      attributes: true, attributeFilter: ['title', 'placeholder', 'aria-label'] })
  }
  scheduleTranslation()
}
