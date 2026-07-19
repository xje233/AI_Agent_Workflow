import axios from 'axios'
import { message } from 'antd'

const request = axios.create({ baseURL: '/api', timeout: 60000 })

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    message.error(error.response?.data?.detail || '网络错误')
    return Promise.reject(error)
  },
)

export default request
