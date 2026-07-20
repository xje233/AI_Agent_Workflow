// HTTP 客户端：统一 API 基地址、超时和响应错误提示。
import axios from 'axios'
import { message } from 'antd'

const request = axios.create({ baseURL: '/api', timeout: 60000 })

// 成功时直接解包业务数据，失败时在全局提示后将错误继续抛给调用方处理。
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    message.error(error.response?.data?.detail || '网络错误')
    return Promise.reject(error)
  },
)

export default request
