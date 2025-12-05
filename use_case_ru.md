# 💰 Campaign Budget: $500 - Complete Use Case

Пример полного рабочего сценария использования API рекламной платформы с бюджетом $500. Покажем как создать, настроить и запустить кампанию шаг за шагом.

## 🎯 Сценарий
У нас есть $500 на тестовую кампанию по продаже онлайн-курса. Хотим протестировать две посадочные страницы и два оффера с разными payout'ами.

## 📋 Предварительные настройки

### 1. Проверка здоровья API
```bash
curl -X GET "http://127.0.0.1:8000/v1/health"
```

**Ответ:**
```json
{
  "status": "healthy",
  "service": "domain-driven-api-mock",
  "instance": "single",
  "port": "8000",
  "hostname": "your-server",
  "timestamp": 1640995200.123
}
```

## 🚀 Шаг 1: Создание кампании

Создаем кампанию с общим бюджетом $500 и дневным лимитом $50 (10 дней кампании).

```bash
curl -X POST "http://127.0.0.1:8000/v1/campaigns" \
  -H "Authorization: Bearer test_jwt_token_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Online Course Sales - $500 Test",
    "description": "Testing two landing pages and offers for online course promotion",
    "whiteUrl": "https://example.com/safe-landing",
    "blackUrl": "https://affiliate.com/course-offer",
    "costModel": "CPA",
    "payout": {
      "amount": 25.00,
      "currency": "USD"
    },
    "dailyBudget": {
      "amount": 50.00,
      "currency": "USD"
    },
    "totalBudget": {
      "amount": 500.00,
      "currency": "USD"
    },
    "startDate": "2024-01-15T00:00:00Z",
    "endDate": "2024-01-25T23:59:59Z"
  }'
```

**Ответ (201 Created):**
```json
{
  "id": "camp_789123",
  "name": "Online Course Sales - $500 Test",
  "description": "Testing two landing pages and offers for online course promotion",
  "status": "draft",
  "schedule": {
    "startDate": "2024-01-15T00:00:00Z",
    "endDate": "2024-01-25T23:59:59Z"
  },
  "urls": {
    "safePage": "https://example.com/safe-landing",
    "offerPage": "https://affiliate.com/course-offer"
  },
  "financial": {
    "costModel": "CPA",
    "payout": {
      "amount": 25.00,
      "currency": "USD"
    },
    "dailyBudget": {
      "amount": 50.00,
      "currency": "USD"
    },
    "totalBudget": {
      "amount": 500.00,
      "currency": "USD"
    },
    "spent": {
      "amount": 0.00,
      "currency": "USD"
    }
  },
  "performance": {
    "clicks": 0,
    "conversions": 0,
    "ctr": 0.0,
    "cr": 0.0,
    "epc": {
      "amount": 0.0,
      "currency": "USD"
    },
    "roi": 0.0
  },
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:00:00Z",
  "_links": {
    "self": "/api/v1/campaigns/camp_789123",
    "landingPages": "/api/v1/campaigns/camp_789123/landing-pages",
    "offers": "/api/v1/campaigns/camp_789123/offers",
    "analytics": "/api/v1/campaigns/camp_789123/analytics"
  }
}
```

## 🎨 Шаг 2: Создание посадочных страниц (A/B тестирование)

Создаем две посадочные страницы с разными весами для A/B тестирования.

### Страница A: Основная (70% трафика)
```bash
curl -X POST "http://127.0.0.1:8000/v1/campaigns/camp_789123/landing-pages" \
  -H "Authorization: Bearer test_jwt_token_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Course Landing Page A - Main",
    "url": "https://example.com/course-landing-a",
    "pageType": "squeeze",
    "weight": 70
  }'
```

**Ответ (201 Created):**
```json
{
  "id": "lp_456001",
  "campaignId": "camp_789123",
  "name": "Course Landing Page A - Main",
  "url": "https://example.com/course-landing-a",
  "pageType": "squeeze",
  "weight": 70,
  "isActive": true,
  "isControl": true,
  "performance": {
    "impressions": 0,
    "clicks": 0,
    "conversions": 0,
    "ctr": 0.0,
    "cr": 0.0,
    "epc": {
      "amount": 0.0,
      "currency": "USD"
    }
  },
  "createdAt": "2024-01-15T10:05:00Z",
  "updatedAt": "2024-01-15T10:05:00Z"
}
```

### Страница B: Альтернативная (30% трафика)
```bash
curl -X POST "http://127.0.0.1:8000/v1/campaigns/camp_789123/landing-pages" \
  -H "Authorization: Bearer test_jwt_token_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Course Landing Page B - Alternative",
    "url": "https://example.com/course-landing-b",
    "pageType": "squeeze",
    "weight": 30
  }'
```

## 💰 Шаг 3: Создание офферов

Создаем два оффера с разными payout'ами для тестирования.

### Оффер 1: Основной ($25 payout, 60% трафика)
```bash
curl -X POST "http://127.0.0.1:8000/v1/campaigns/camp_789123/offers" \
  -H "Authorization: Bearer test_jwt_token_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Online Course Premium - $25",
    "url": "https://affiliate.com/course-premium",
    "offerType": "direct",
    "weight": 60,
    "payout": {
      "amount": 25.00,
      "currency": "USD"
    },
    "revenueShare": 0.15,
    "costPerClick": {
      "amount": 2.50,
      "currency": "USD"
    },
    "externalId": "COURSE_PREMIUM_25",
    "partnerNetwork": "MaxBounty"
  }'
```

### Оффер 2: Альтернативный ($30 payout, 40% трафика)
```bash
curl -X POST "http://127.0.0.1:8000/v1/campaigns/camp_789123/offers" \
  -H "Authorization: Bearer test_jwt_token_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Online Course Deluxe - $30",
    "url": "https://affiliate.com/course-deluxe",
    "offerType": "direct",
    "weight": 40,
    "payout": {
      "amount": 30.00,
      "currency": "USD"
    },
    "revenueShare": 0.18,
    "costPerClick": {
      "amount": 3.00,
      "currency": "USD"
    },
    "externalId": "COURSE_DELUXE_30",
    "partnerNetwork": "ClickBank"
  }'
```

## ▶️ Шаг 4: Запуск кампании

Запускаем кампанию после настройки всех компонентов.

```bash
curl -X POST "http://127.0.0.1:8000/v1/campaigns/camp_789123/resume" \
  -H "Authorization: Bearer test_jwt_token_12345"
```

**Ответ (200 OK):**
```json
{
  "id": "camp_789123",
  "name": "Online Course Sales - $500 Test",
  "status": "active",
  "updatedAt": "2024-01-15T10:15:00Z"
}
```

## 📊 Шаг 5: Мониторинг производительности

### Проверка аналитики кампании
```bash
curl -X GET "http://127.0.0.1:8000/v1/campaigns/camp_789123/analytics?startDate=2024-01-15&endDate=2024-01-15&granularity=day" \
  -H "Authorization: Bearer test_jwt_token_12345"
```

### Проверка списка посадочных страниц
```bash
curl -X GET "http://127.0.0.1:8000/v1/campaigns/camp_789123/landing-pages" \
  -H "Authorization: Bearer test_jwt_token_12345"
```

### Проверка списка офферов
```bash
curl -X GET "http://127.0.0.1:8000/v1/campaigns/camp_789123/offers" \
  -H "Authorization: Bearer test_jwt_token_12345"
```

## 🎯 Шаг 6: Тестирование трафика

### Отправка тестового клика
```bash
curl -L "http://127.0.0.1:8000/v1/click?cid=789123&sub1=facebook&sub2=ad_campaign&sub3=prospecting&click_id=test_click_001"
```

### Проверка списка кликов
```bash
curl -X GET "http://127.0.0.1:8000/v1/clicks?cid=789123&limit=10" \
  -H "Authorization: Bearer test_jwt_token_12345" \
  -H "X-API-Key: test_api_key_abcdef123"
```

## ⏹️ Шаг 7: Управление кампанией

### Приостановка кампании (если нужно сэкономить бюджет)
```bash
curl -X POST "http://127.0.0.1:8000/v1/campaigns/camp_789123/pause" \
  -H "Authorization: Bearer test_jwt_token_12345" \
  -d '{"reason": "Temporary budget adjustment"}'
```

### Обновление бюджета (если результаты хорошие)
```bash
curl -X PUT "http://127.0.0.1:8000/v1/campaigns/camp_789123" \
  -H "Authorization: Bearer test_jwt_token_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "dailyBudget": {
      "amount": 75.00,
      "currency": "USD"
    },
    "totalBudget": {
      "amount": 750.00,
      "currency": "USD"
    }
  }'
```

## 📈 Финальный отчет

### Итоговая аналитика
```bash
curl -X GET "http://127.0.0.1:8000/v1/campaigns/camp_789123/analytics?startDate=2024-01-15&endDate=2024-01-25" \
  -H "Authorization: Bearer test_jwt_token_12345"
```

**Ожидаемый результат:**
```json
{
  "campaignId": "camp_789123",
  "timeRange": {
    "startDate": "2024-01-15",
    "endDate": "2024-01-25",
    "granularity": "day"
  },
  "metrics": {
    "clicks": 8500,
    "uniqueClicks": 8200,
    "conversions": 85,
    "revenue": {
      "amount": 2387.50,
      "currency": "USD"
    },
    "cost": {
      "amount": 425.00,
      "currency": "USD"
    },
    "ctr": 0.034,
    "cr": 0.01,
    "epc": {
      "amount": 28.09,
      "currency": "USD"
    },
    "roi": 4.62
  }
}
```

## 💡 Ключевые insights из этого use case:

1. **Бюджетное планирование**: $500 распределено на 10 дней с дневным лимитом $50
2. **A/B тестирование**: 70/30% распределение трафика между landing pages
3. **Тестирование офферов**: Два оффера с разными payout'ами (25$ vs 30$)
4. **Мониторинг**: Регулярная проверка аналитики для оптимизации
5. **Гибкость**: Возможность корректировки бюджета и весов на лету

## 🎯 Результат: ROI 462% при конверсии 1% и EPC $28.09

Этот сценарий показывает полный жизненный цикл рекламной кампании от создания до анализа результатов с использованием всех основных функций API платформы! 🚀
