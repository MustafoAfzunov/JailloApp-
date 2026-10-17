import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { setApiLang } from './api.js'

const ky = {
  brand: { name: 'Жайлоо', tagline: 'Айыл коопсуздугу жана базар' },
  nav: { home: 'Башкы', map: 'Карта', market: 'Базар', sell: 'Сатуу', help: 'Жардам', profile: 'Профиль', login: 'Кирүү' },
  common: { close: 'Жабуу', loading: 'Жүктөлүүдө…', error: 'Ката кетти. Кайра аракет кылыңыз.', retry: 'Кайра', cancel: 'Жокко чыгаруу', back: 'Артка', m: 'м', min: 'мүн', som: 'сом' },
  alertbar: { open: 'Ачуу' },
  footer: { title: 'Жайлоо', sub: 'Айыл коопсуздугу жана базар', code112: 'Куткаруу: 112', hub: 'Колдоо' },
  home: {
    pill: { calm: 'Тынч', watch: 'Көзөмөл', danger: 'Коркунуч' }, openAlert: 'Сигналды ачуу', weather: 'Аба ырайы',
    audioTitle: 'Угуп алыңыз', audioSub: 'Абалды үн менен окуйбуз', audioStart: 'Угуу', audioStop: 'Токтотуу',
    mapBadge: 'Коопсуздук', mapTitle: 'Коопсуздук картасы', mapText: 'Коркунучтуу жана коопсуз аймактар, качуу жолдору.', shelters: '{n} коопсуз жай', mapCta: 'Картаны ачуу',
    marketBadge: '{n} жаңы', marketTitle: 'Айыл базары', marketText: 'Сүт, кымыз, бал, мал — түз сатуучудан.', marketCaption: 'Ортомчусуз, төлөмсүз', marketCta: 'Базарга кирүү',
    emergencyTitle: 'Шашылыш жардам', emergencyText: 'Коркунуч болсо дароо чалыңыз.', call112: '112', call112Sub: 'Куткаруу кызматы',
  },
  role: { head: 'Айыл башчысы', ambulance: 'Тез жардам', emergency: 'Шашылыш кызмат', vet: 'Ветеринар', medic: 'Фельдшер', pasture: 'Жайыт комитети', transport: 'Транспорт', support: 'Колдоо', user: { villager: 'Тургун', rescuer: 'Куткаруучу', admin: 'Админ', buyer: 'Сатып алуучу' } },
  map: {
    live: 'Түз эфир', service: 'Коопсуздук кызматы', listen: 'Угуу', current: 'Азыркы абал', updated: 'Жаңыртылды', shelterTag: 'Коопсуз жай', mainShelter: 'Башкы жай', shelter: 'Жай', walk: 'Жөө',
    clinic: 'ФАП', doctor: 'Дарыгер бар', water: 'Суу бар', tank: 'Суу сактагыч', showRoute: '«{name}» жолун көрсөтүү', routeText: '{name} — {dist}', legend: 'Белгилер',
    legendSafe: 'Коопсуз', legendSafeText: 'Бийик жана бекем жер', legendDanger: 'Коркунуч', legendDangerText: 'Сел өтүүчү өзөн', legendYou: 'Сиз', legendYouText: 'Сиздин үй',
    report: 'Коркунучту билдирүү', you: 'Сиз', dangerLabel: 'Сел коркунучу', n: 'Т', s: 'Ш', e: 'Ч', w: 'Б', direction: 'Багыт', northUp: 'Түндүк жогоруда', zoomIn: 'Чоңойтуу', zoomOut: 'Кичирейтүү',
  },
  report: { title: 'Эмне болду?', question: 'Коркунучтун түрүн тандаңыз', needLogin: 'Билдирүү үчүн кириңиз', flood: 'Сел / суу', rockfall: 'Таш жыгылуу', avalanche: 'Кар көчкү', fire: 'Өрт / түтүн', sent: 'Рахмат! Билдирүү жөнөтүлдү.' },
  market: {
    order: 'Буйрутма', left: '{n} калды', pickup: 'Өзү барат', delivery: 'Жеткирүү', notePlaceholder: 'Сатуучуга билдирүү (милдеттүү эмес)', total: 'Жалпы', phoneNote: 'Сатуучу кабыл алгандан кийин телефон көрүнөт.',
    sendOrder: 'Буйрутма жөнөтүү', orderSent: 'Буйрутма жөнөтүлдү', today: 'Бүгүн', available: '{n} {unit} бар', price: 'Баасы', villageAlert: 'Айылда коркунуч бар — жолдор жабык болушу мүмкүн.', yours: 'Сиздин жарыя',
    call: 'Чалуу', chat: 'Чат', topNote: 'Түз сатуучудан', noMiddle: 'Ортомчусуз', support: 'Колдоо', badge: 'Айыл базары', title: 'Жайлоо базары', sub: 'Тоо айылдарынын жергиликтүү азыктары', addNew: 'Жарыя берүү',
    searchPlaceholder: 'Эмне издейсиз?', search: 'Издөө', voice: 'Үн менен', listening: 'Угуп жатам…', noVoice: 'Браузер үн таануусун колдобойт', pickSection: 'Бөлүм тандаңыз', listings: 'Жарыялар', count: '{n}', sort: 'Иреттөө', newest: 'Жаңылар',
    empty: 'Азырынча жарыя жок.', transportTitle: 'Транспорт керекпи?', transportText: 'Жүктү жеткирүү үчүн айдоочуга чалыңыз.', callTransport: 'Айдоочуга чалуу', haveGoods: 'Сатчу товарыңыз барбы?', haveGoodsText: 'Сүрөткө тартып, 1 мүнөттө жарыя бериңиз.',
    newListing: 'Жаңы жарыя', more: 'Дагы көрсөтүү', adviceLabel: 'Кеңеш', adviceTitle: 'Жакшы сүрөт — тез сатуу', adviceText: 'Товарды жарык жерде тартыңыз.', needHelp: 'Жардам керекпи?',
  },
  unit: { kg: 'кг', l: 'л', piece: 'даана', head: 'баш', jar: 'банка', bottle: 'бөтөлкө' },
  sell: {
    title: 'Жарыя берүү', sub: 'Төрт кадам', needVillage: 'Профилде айылыңызды тандаңыз', step1: '1. Сүрөт', step2: '2. Аты жана көлөмү', step3: '3. Баасы', step4: '4. Бөлүм',
    photoTitle: 'Товардын сүрөтү', photoSub: 'Сүрөткө тартыңыз же тандаңыз', pickPhoto: 'Сүрөт тандоо', photoReady: 'Сүрөт даяр', photoClear: 'Өчүрүү', otherPhoto: 'Башка сүрөт',
    namePlaceholder: 'Мисалы: Таза бал', amount: 'Көлөмү', needName: 'Атын жазыңыз', som: 'сом', somShort: 'сом', quick: 'Тез баа', priceFor: '1 {unit} үчүн баа',
    yourPhone: 'Сиздин телефон', phoneHidden: 'Сатуучу кабыл алганда гана көрүнөт', verified: 'Текшерилген сатуучу', publish: 'Жарыялоо', done: 'Жарыя берилди!', doneSub: 'Эми сатып алуучулар көрө алат.',
  },
  login: {
    title: 'Кирүү', sub: 'Телефон номериңизди жазыңыз', phone: 'Телефон', getCode: 'Код алуу', howTitle: 'Код кантип келет', how1: 'Telegram’да {bot} ботун ачыңыз', how2: 'Телефон номериңизди бөлүшүңүз', how3: 'Бот код жөнөтөт — аны ушул жерге жазыңыз',
    openBot: 'Ботту ачуу', demoTitle: 'Демо аккаунттар', demoVillager: 'Тургун', demoRescuer: 'Куткаруучу', demoBuyer: 'Сатып алуучу',
    sentTelegram: 'Код Telegram’га жөнөтүлдү.', sentDev: 'Тест режими: код төмөндө.', sentNone: 'Алгач {bot} ботун Telegram’да ачып, номериңизди бириктириңиз.', devCode: 'Тест коду', code: 'Код', yourName: 'Атыңыз', enter: 'Кирүү', changeNumber: 'Номерди өзгөртүү',
  },
  alert: {
    none: 'Азыр коркунуч жок', noneSub: 'Сигнал болсо, бул жерден көрөсүз.', demo: 'ТЕСТ', arrives: 'Жетүүгө чейин', doNow: 'Азыр эмне кылуу керек', showRoute: 'Качуу жолун көрсөтүү', imSafe: 'Мен коопсузмун',
    safeDone: 'Белгиленди', safeThanks: 'Рахмат, сиз коопсуз экениңиз белгиленди.', safeCount: '{n} киши коопсуз',
    steps: {
      mudflow: ['Дароо бийик жерге чыгыңыз', 'Дарыянын боюнан алыс болуңуз', 'Малды жана үйдү калтырыңыз', 'Кошуналарга эскертиңиз', '112 чалыңыз'],
      flood: ['Бийик жерге чыгыңыз', 'Суунун ичинде жүрбөңүз', 'Электрди өчүрүңүз', 'Документ жана дары алыңыз', '112 чалыңыз'],
      avalanche: ['Эңиштен алыс болуңуз', 'Тоодон түшүп бараткан кардан капталга качыңыз', 'Көмүлсөңүз — оозуңузду жаап, кыймылдаңыз', 'Башкаларга жардам бериңиз', '112 чалыңыз'],
      fire: ['Шамалга каршы жактан чыгыңыз', 'Оозуңузду нымдуу кездеме менен жабыңыз', 'Малды чыгарыңыз', 'Суу бар жерге барыңыз', '112 чалыңыз'],
    },
  },
  level: { low: 'Төмөн', medium: 'Орто', high: 'Жогору', critical: 'Өтө коркунучтуу' },
  hazard: { mudflow: 'Сел', flood: 'Суу ташкыны', avalanche: 'Кар көчкү', fire: 'Өрт' },
  help: { title: 'Жардам', sub: 'Коркунучта эмне кылуу керек', call112: '112 чалуу', whatToDo: 'Эмне кылуу керек', howTo: 'Колдонмо кантип иштейт', how1: 'Сенсорлор жана спутник коркунучту алдын ала байкайт.', how2: 'Базарда түз сатуучудан сатып алыңыз.', how3: 'Сигнал Telegram’га келет.', contacts: 'Маанилүү номерлер', loginHint: 'Кирүү' },
  orders: {
    title: 'Буйрутмалар', tab: { buyer: 'Мен алам', seller: 'Мен сатам' }, status: { pending: 'Күтүүдө', accepted: 'Кабыл алынды', declined: 'Четке кагылды', completed: 'Аткарылды', cancelled: 'Жокко чыкты' },
    seller: 'Сатуучу', buyer: 'Сатып алуучу', call: 'Чалуу', accept: 'Кабыл алуу', decline: 'Четке кагуу', complete: 'Аткарылды', cancel: 'Жокко чыгаруу', review: 'Баа берүү', rateSeller: 'Сатуучуга баа бериңиз', commentPlaceholder: 'Пикир (милдеттүү эмес)', sendReview: 'Жөнөтүү',
    thanks: 'Пикириңиз үчүн рахмат!', updated: 'Жаңыртылды', empty: 'Буйрутма жок',
  },
  chats: { title: 'Чаттар', empty: 'Чат жок', pick: 'Чатты тандаңыз', placeholder: 'Билдирүү жазыңыз…', send: 'Жөнөтүү', startHint: 'Сатуучу менен сүйлөшүүнү баштаңыз' },
  profile: {
    about: 'Мен жөнүндө', village: 'Айыл', save: 'Сактоо', saved: 'Сакталды', home: 'Менин үйүм', homeHint: 'Картада үйүңүз көрүнөт.', houseNo: 'Үй номери', useGps: 'GPS менен белгилөө', homeSet: 'Үй белгиленди', homeSaved: 'Үй сакталды', noGeo: 'Жайгашуу аныкталган жок',
    language: 'Тил', tgLinked: 'Telegram байланышкан', tgNot: 'Telegram байланышкан эмес', myListings: 'Менин жарыяларым', noListings: 'Жарыя жок', closeListing: 'Жабуу', listingClosed: 'Жарыя жабылды', logout: 'Чыгуу',
    rescuer: 'Куткаруучу панели', rescuerHint: 'Тест сигналын жөнөтүү.', fireAlert: 'Сигнал жөнөтүү', clearAlerts: 'Сигналдарды өчүрүү', alertSent: 'Сигнал жөнөтүлдү', alertCleared: 'Сигналдар өчүрүлдү',
  },
}

const ru = {
  brand: { name: 'Жайлоо', tagline: 'Безопасность села и рынок' },
  nav: { home: 'Главная', map: 'Карта', market: 'Рынок', sell: 'Продать', help: 'Помощь', profile: 'Профиль', login: 'Войти' },
  common: { close: 'Закрыть', loading: 'Загрузка…', error: 'Произошла ошибка. Повторите.', retry: 'Повторить', cancel: 'Отмена', back: 'Назад', m: 'м', min: 'мин', som: 'сом' },
  alertbar: { open: 'Открыть' },
  footer: { title: 'Жайлоо', sub: 'Безопасность села и рынок', code112: 'Спасатели: 112', hub: 'Поддержка' },
  home: {
    pill: { calm: 'Спокойно', watch: 'Наблюдаем', danger: 'Опасность' }, openAlert: 'Открыть сигнал', weather: 'Погода',
    audioTitle: 'Послушайте', audioSub: 'Прочитаем обстановку вслух', audioStart: 'Слушать', audioStop: 'Стоп',
    mapBadge: 'Безопасность', mapTitle: 'Карта безопасности', mapText: 'Опасные и безопасные зоны, пути эвакуации.', shelters: '{n} безопасных мест', mapCta: 'Открыть карту',
    marketBadge: '{n} новых', marketTitle: 'Сельский рынок', marketText: 'Молоко, кымыз, мёд, скот — напрямую от продавца.', marketCaption: 'Без посредников и платежей', marketCta: 'Перейти на рынок',
    emergencyTitle: 'Экстренная помощь', emergencyText: 'При опасности звоните сразу.', call112: '112', call112Sub: 'Служба спасения',
  },
  role: { head: 'Глава села', ambulance: 'Скорая помощь', emergency: 'Экстренная служба', vet: 'Ветеринар', medic: 'Фельдшер', pasture: 'Комитет пастбищ', transport: 'Транспорт', support: 'Поддержка', user: { villager: 'Житель', rescuer: 'Спасатель', admin: 'Админ', buyer: 'Покупатель' } },
  map: {
    live: 'В прямом эфире', service: 'Служба безопасности', listen: 'Слушать', current: 'Текущая обстановка', updated: 'Обновлено', shelterTag: 'Безопасное место', mainShelter: 'Главное укрытие', shelter: 'Укрытие', walk: 'Пешком',
    clinic: 'ФАП', doctor: 'Есть врач', water: 'Есть вода', tank: 'Водонапорная башня', showRoute: 'Показать путь: {name}', routeText: '{name} — {dist}', legend: 'Обозначения',
    legendSafe: 'Безопасно', legendSafeText: 'Высокое и прочное место', legendDanger: 'Опасно', legendDangerText: 'Русло селя', legendYou: 'Вы', legendYouText: 'Ваш дом',
    report: 'Сообщить об опасности', you: 'Вы', dangerLabel: 'Угроза селя', n: 'С', s: 'Ю', e: 'В', w: 'З', direction: 'Направление', northUp: 'Север вверху', zoomIn: 'Приблизить', zoomOut: 'Отдалить',
  },
  report: { title: 'Что случилось?', question: 'Выберите тип опасности', needLogin: 'Войдите, чтобы сообщить', flood: 'Сель / вода', rockfall: 'Камнепад', avalanche: 'Лавина', fire: 'Пожар / дым', sent: 'Спасибо! Сообщение отправлено.' },
  market: {
    order: 'Заказать', left: 'Осталось {n}', pickup: 'Самовывоз', delivery: 'Доставка', notePlaceholder: 'Сообщение продавцу (необязательно)', total: 'Итого', phoneNote: 'Телефон продавца откроется после принятия заказа.',
    sendOrder: 'Отправить заказ', orderSent: 'Заказ отправлен', today: 'Сегодня', available: 'В наличии: {n} {unit}', price: 'Цена', villageAlert: 'В селе опасность — дороги могут быть закрыты.', yours: 'Ваше объявление',
    call: 'Позвонить', chat: 'Чат', topNote: 'Напрямую от продавца', noMiddle: 'Без посредников', support: 'Поддержка', badge: 'Сельский рынок', title: 'Рынок Жайлоо', sub: 'Местные продукты горных сёл', addNew: 'Подать объявление',
    searchPlaceholder: 'Что ищете?', search: 'Поиск', voice: 'Голосом', listening: 'Слушаю…', noVoice: 'Браузер не поддерживает голосовой ввод', pickSection: 'Выберите раздел', listings: 'Объявления', count: '{n}', sort: 'Сортировка', newest: 'Новые',
    empty: 'Пока нет объявлений.', transportTitle: 'Нужен транспорт?', transportText: 'Позвоните водителю, чтобы доставить груз.', callTransport: 'Позвонить водителю', haveGoods: 'Есть что продать?', haveGoodsText: 'Сфотографируйте и подайте объявление за минуту.',
    newListing: 'Новое объявление', more: 'Показать ещё', adviceLabel: 'Совет', adviceTitle: 'Хорошее фото — быстрая продажа', adviceText: 'Снимайте товар при хорошем свете.', needHelp: 'Нужна помощь?',
  },
  unit: { kg: 'кг', l: 'л', piece: 'шт', head: 'гол.', jar: 'банка', bottle: 'бутылка' },
  sell: {
    title: 'Подать объявление', sub: 'Четыре шага', needVillage: 'Выберите село в профиле', step1: '1. Фото', step2: '2. Название и количество', step3: '3. Цена', step4: '4. Раздел',
    photoTitle: 'Фото товара', photoSub: 'Сфотографируйте или выберите', pickPhoto: 'Выбрать фото', photoReady: 'Фото готово', photoClear: 'Удалить', otherPhoto: 'Другое фото',
    namePlaceholder: 'Например: Горный мёд', amount: 'Количество', needName: 'Введите название', som: 'сом', somShort: 'сом', quick: 'Быстрая цена', priceFor: 'Цена за 1 {unit}',
    yourPhone: 'Ваш телефон', phoneHidden: 'Виден только после принятия заказа', verified: 'Проверенный продавец', publish: 'Опубликовать', done: 'Объявление опубликовано!', doneSub: 'Теперь его увидят покупатели.',
  },
  login: {
    title: 'Вход', sub: 'Введите номер телефона', phone: 'Телефон', getCode: 'Получить код', howTitle: 'Как приходит код', how1: 'Откройте бота {bot} в Telegram', how2: 'Поделитесь номером телефона', how3: 'Бот пришлёт код — введите его здесь',
    openBot: 'Открыть бота', demoTitle: 'Демо-аккаунты', demoVillager: 'Житель', demoRescuer: 'Спасатель', demoBuyer: 'Покупатель',
    sentTelegram: 'Код отправлен в Telegram.', sentDev: 'Тестовый режим: код ниже.', sentNone: 'Сначала откройте бота {bot} в Telegram и привяжите номер.', devCode: 'Тестовый код', code: 'Код', yourName: 'Ваше имя', enter: 'Войти', changeNumber: 'Изменить номер',
  },
  alert: {
    none: 'Сейчас опасности нет', noneSub: 'Если будет сигнал, вы увидите его здесь.', demo: 'ТЕСТ', arrives: 'До прихода', doNow: 'Что делать сейчас', showRoute: 'Показать путь эвакуации', imSafe: 'Я в безопасности',
    safeDone: 'Отмечено', safeThanks: 'Спасибо, вы отмечены как в безопасности.', safeCount: '{n} чел. в безопасности',
    steps: {
      mudflow: ['Срочно поднимитесь выше', 'Уйдите от русла реки', 'Оставьте скот и вещи', 'Предупредите соседей', 'Позвоните 112'],
      flood: ['Поднимитесь на возвышенность', 'Не заходите в воду', 'Отключите электричество', 'Возьмите документы и лекарства', 'Позвоните 112'],
      avalanche: ['Уйдите с склона', 'Уходите в сторону от движения снега', 'Если засыпало — закройте рот и двигайтесь', 'Помогите другим', 'Позвоните 112'],
      fire: ['Уходите против ветра', 'Закройте лицо влажной тканью', 'Выведите скот', 'Идите к воде', 'Позвоните 112'],
    },
  },
  level: { low: 'Низкий', medium: 'Средний', high: 'Высокий', critical: 'Критический' },
  hazard: { mudflow: 'Сель', flood: 'Наводнение', avalanche: 'Лавина', fire: 'Пожар' },
  help: { title: 'Помощь', sub: 'Что делать при опасности', call112: 'Позвонить 112', whatToDo: 'Что делать', howTo: 'Как работает приложение', how1: 'Датчики и спутники заранее замечают опасность.', how2: 'На рынке покупайте напрямую у продавца.', how3: 'Сигнал придёт в Telegram.', contacts: 'Важные номера', loginHint: 'Войти' },
  orders: {
    title: 'Заказы', tab: { buyer: 'Я покупаю', seller: 'Я продаю' }, status: { pending: 'Ожидает', accepted: 'Принят', declined: 'Отклонён', completed: 'Выполнен', cancelled: 'Отменён' },
    seller: 'Продавец', buyer: 'Покупатель', call: 'Позвонить', accept: 'Принять', decline: 'Отклонить', complete: 'Выполнен', cancel: 'Отменить', review: 'Оценить', rateSeller: 'Оцените продавца', commentPlaceholder: 'Отзыв (необязательно)', sendReview: 'Отправить',
    thanks: 'Спасибо за отзыв!', updated: 'Обновлено', empty: 'Заказов нет',
  },
  chats: { title: 'Чаты', empty: 'Чатов нет', pick: 'Выберите чат', placeholder: 'Напишите сообщение…', send: 'Отправить', startHint: 'Начните разговор с продавцом' },
  profile: {
    about: 'Обо мне', village: 'Село', save: 'Сохранить', saved: 'Сохранено', home: 'Мой дом', homeHint: 'Ваш дом будет виден на карте.', houseNo: 'Номер дома', useGps: 'Отметить по GPS', homeSet: 'Дом отмечен', homeSaved: 'Дом сохранён', noGeo: 'Не удалось определить местоположение',
    language: 'Язык', tgLinked: 'Telegram привязан', tgNot: 'Telegram не привязан', myListings: 'Мои объявления', noListings: 'Объявлений нет', closeListing: 'Закрыть', listingClosed: 'Объявление закрыто', logout: 'Выйти',
    rescuer: 'Панель спасателя', rescuerHint: 'Отправить тестовый сигнал.', fireAlert: 'Отправить сигнал', clearAlerts: 'Снять сигналы', alertSent: 'Сигнал отправлен', alertCleared: 'Сигналы сняты',
  },
}

const DICT = { ky, ru }
const lookup = (obj, key) => key.split('.').reduce((o, k) => (o == null ? o : o[k]), obj)
const read = () => { try { const v = localStorage.getItem('jailo.lang'); return v === 'ru' || v === 'ky' ? v : 'ky' } catch { return 'ky' } }

const Ctx = createContext(null)

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(read)
  useEffect(() => { setApiLang(lang); document.documentElement.lang = lang }, [lang])
  const setLang = useCallback((l) => { setLangState(l); try { localStorage.setItem('jailo.lang', l) } catch { /* ignore */ } }, [])
  const t = useCallback((key, vars) => {
    const v = lookup(DICT[lang], key) ?? lookup(ru, key)
    if (v == null) return key
    if (typeof v !== 'string' || !vars) return v
    return v.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? ''))
  }, [lang])
  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useI18n = () => useContext(Ctx)
