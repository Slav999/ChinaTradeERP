import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { chatReferenceTitle, translateChatText } from './chatTranslations.js'
const require = createRequire(import.meta.url)
const { parse } = require('@vue/compiler-sfc')
const { parse: parseTemplate } = require('@vue/compiler-dom')
const { parse: parseScript } = require('@babel/parser')

test('chat labels, tooltips and dynamic read counts translate between Russian and English', () => {
  assert.equal(translateChatText('  Очистить поиск ', 'en'), '  Clear search ')
  assert.equal(translateChatText('Clear search', 'ru'), 'Очистить поиск')
  assert.equal(translateChatText('Прочитали 3 из 5', 'en'), 'Read by 3 of 5')
  assert.equal(translateChatText('Убрать Иван из группы', 'en'), 'Remove Иван from group')
  assert.equal(translateChatText('Файлы компании: 2.0 МБ из 5.0 ГБ', 'en'), 'Company files: 2.0 MB of 5.0 GB')
  assert.equal(translateChatText('Иван создал(а) группу «Продажи».', 'en'), 'Иван created the group “Продажи”.')
})

test('record names remain user content; only generated order labels are translated', () => {
  assert.equal(chatReferenceTitle({ type: 'product', title: 'Товар' }, 'en'), 'Товар')
  assert.equal(chatReferenceTitle({ type: 'counterparty', title: 'Сохранить' }, 'en'), 'Сохранить')
  assert.equal(chatReferenceTitle({ type: 'customer_order', title: 'Заказ покупателя №25 / 2026' }, 'en'), 'Customer order №25 / 2026')
  assert.equal(chatReferenceTitle({ type: 'supplier_order', title: 'Заказ поставщику №8' }, 'ru'), 'Заказ поставщику №8')
})

test('static chat text, placeholders and accessibility labels have English translations', () => {
  const missing = new Set()
  for (const name of ['CompanyChat', 'ChatMessageItem', 'ChatResources', 'ChatAttachment', 'ChatShareButton', 'RelatedChatsButton', 'ChatRecordPreview']) {
    const source = readFileSync(new URL(`../components/${name}.vue`, import.meta.url), 'utf8')
    const { descriptor } = parse(source)
    function visit(node, skip = false) {
      skip ||= node.props?.some(prop => prop.name === 'data-i18n-skip')
      if (skip) return
      const check = text => {
        if (/[А-Яа-яЁё]/u.test(text) && translateChatText(text, 'en') === text) missing.add(`${name}: ${text.trim()}`)
      }
      if (node.type === 2) check(node.content)
      for (const prop of node.props || []) {
        if (['title', 'placeholder', 'aria-label'].includes(prop.name) && prop.value) check(prop.value.content)
      }
      node.children?.forEach(child => visit(child, skip))
    }
    visit(parseTemplate(descriptor.template.content))
    function visitScript(node) {
      if (!node || typeof node !== 'object') return
      if (node.type === 'StringLiteral' && /[А-Яа-яЁё]/u.test(node.value) && translateChatText(node.value, 'en') === node.value) {
        missing.add(`${name}: ${node.value}`)
      }
      Object.values(node).forEach(value => {
        if (Array.isArray(value)) value.forEach(visitScript)
        else if (value && typeof value === 'object') visitScript(value)
      })
    }
    visitScript(parseScript((descriptor.scriptSetup || descriptor.script).content, { sourceType: 'module' }))
  }
  assert.deepEqual([...missing], [])
})
