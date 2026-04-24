import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Switch,
  Button,
  Space,
  message,
  Select,
  InputNumber,
  Typography,
  Divider,
  Alert,
  Row,
  Col,
  Image,
  Spin
} from 'antd';
import { PictureOutlined, ExperimentOutlined } from '@ant-design/icons';
import { imageGenApi } from '@/services/api';
import { Link } from 'react-router-dom';

const { Title, Text } = Typography;

interface ImageGenConfig {
  enabled: boolean;
  provider: string;
  modelscope: {
    api_key: string;
    model: string;
    timeout: number;
  };
  yunwu: {
    api_key: string;
    api_base: string;
    model: string;
    timeout: number;
  };
  trigger_keywords: string[];
  generating_message: string;
  error_message: string;
  success_message: string;
}

const ImageGenPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [testLoading, setTestLoading] = useState(false);
  const [generateLoading, setGenerateLoading] = useState(false);
  const [testImage, setTestImage] = useState<string | null>(null);
  const [config, setConfig] = useState<ImageGenConfig>({
    enabled: true,
    provider: 'modelscope',
    modelscope: {
      api_key: '',
      model: 'Tongyi-MAI/Z-Image-Turbo',
      timeout: 120
    },
    yunwu: {
      api_key: '',
      api_base: 'https://yunwu.ai/v1',
      model: 'jimeng-4.5',
      timeout: 120
    },
    trigger_keywords: ['画', '生成图片', '生图', '绘制'],
    generating_message: '🎨 正在为你生成图片，请稍候...',
    error_message: '😢 图片生成失败：{error}',
    success_message: '✨ 图片已生成完成！'
  });

  // 可用的模型列表
  const modelscopeModels = [
    'Tongyi-MAI/Z-Image-Turbo',
    'AI-ModelScope/stable-diffusion-v1-5',
    'AI-ModelScope/stable-diffusion-xl-base-1.0'
  ];

  const yunwuModels = [
    'jimeng-4.5',
    'stable-diffusion-xl',
    'dall-e-3'
  ];

  // 获取当前提供商
  const currentProvider = Form.useWatch('provider', form) || 'modelscope';

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await imageGenApi.getImageGenConfig();
      setConfig(data);
      form.setFieldsValue(data);
    } catch (error) {
      message.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async (values: ImageGenConfig) => {
    try {
      setLoading(true);
      await imageGenApi.updateImageGenConfig(values);
      message.success('配置保存成功');
      setConfig(values);
    } catch (error) {
      message.error('配置保存失败');
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async () => {
    try {
      setTestLoading(true);
      const success = await imageGenApi.testImageGenConnection();
      
      if (success) {
        message.success('连接测试成功');
      } else {
        message.error('连接测试失败');
      }
    } catch (error) {
      message.error('连接测试失败');
    } finally {
      setTestLoading(false);
    }
  };

  const generateTestImage = async () => {
    try {
      setGenerateLoading(true);
      setTestImage(null);
      
      const result = await imageGenApi.generateImage('一只可爱的小猫咪在花园里玩耍');
      
      if (result.success && result.image_data) {
        setTestImage(`data:image/jpeg;base64,${result.image_data}`);
        message.success('测试图片生成成功');
      } else {
        message.error(`图片生成失败：${result.message}`);
      }
    } catch (error) {
      message.error('图片生成失败');
    } finally {
      setGenerateLoading(false);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <PictureOutlined /> 图像生成配置
      </Title>

      <Alert
        message="多用户提示"
        description={
          <div>
            此页面为<strong>全局</strong>图像生成配置；如需为不同用户设置不同的生图提供商/模型/密钥，请到 <Link to="/user-config">个人配置</Link> 页面配置。
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      
      <Row gutter={[24, 24]}>
        <Col span={16}>
          <Card title="基础配置" loading={loading}>
            <Form
              form={form}
              layout="vertical"
              initialValues={config}
              onFinish={saveConfig}
            >
              <Form.Item
                name="enabled"
                label="启用图像生成"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <Form.Item
                name="provider"
                label="提供商"
              >
                <Select>
                  <Select.Option value="modelscope">魔搭社区</Select.Option>
                  <Select.Option value="yunwu">yunwu.ai</Select.Option>
                </Select>
              </Form.Item>

              {currentProvider === 'modelscope' && (
                <>
                  <Divider>魔搭社区配置</Divider>

                  <Form.Item
                    name={['modelscope', 'api_key']}
                    label="API密钥"
                    rules={[{ required: true, message: '请输入API密钥' }]}
                  >
                    <Input.Password placeholder="请输入魔搭社区API密钥" />
                  </Form.Item>

                  <Form.Item
                    name={['modelscope', 'model']}
                    label="模型"
                    rules={[{ required: true, message: '请选择模型' }]}
                  >
                    <Select>
                      {modelscopeModels.map(model => (
                        <Select.Option key={model} value={model}>
                          {model}
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Form.Item
                    name={['modelscope', 'timeout']}
                    label="超时时间（秒）"
                  >
                    <InputNumber min={30} max={300} />
                  </Form.Item>
                </>
              )}

              {currentProvider === 'yunwu' && (
                <>
                  <Divider>yunwu.ai 配置</Divider>

                  <Form.Item
                    name={['yunwu', 'api_key']}
                    label="API密钥"
                    rules={[{ required: true, message: '请输入API密钥' }]}
                  >
                    <Input.Password placeholder="请输入 yunwu.ai API密钥" />
                  </Form.Item>

                  <Form.Item
                    name={['yunwu', 'api_base']}
                    label="API地址"
                  >
                    <Input placeholder="https://yunwu.ai/v1" />
                  </Form.Item>

                  <Form.Item
                    name={['yunwu', 'model']}
                    label="模型"
                    rules={[{ required: true, message: '请选择模型' }]}
                  >
                    <Select>
                      {yunwuModels.map(model => (
                        <Select.Option key={model} value={model}>
                          {model}
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Form.Item
                    name={['yunwu', 'timeout']}
                    label="超时时间（秒）"
                  >
                    <InputNumber min={30} max={300} />
                  </Form.Item>
                </>
              )}

              <Divider>触发配置</Divider>

              <Form.Item
                name="trigger_keywords"
                label="触发关键词"
                rules={[{ required: true, message: '请输入触发关键词' }]}
              >
                <Select
                  mode="tags"
                  placeholder="输入触发关键词，按回车添加"
                  style={{ width: '100%' }}
                />
              </Form.Item>

              <Form.Item
                name="generating_message"
                label="生成中消息"
              >
                <Input placeholder="图片生成时显示的消息" />
              </Form.Item>

              <Form.Item
                name="error_message"
                label="错误消息"
              >
                <Input placeholder="生成失败时显示的消息" />
              </Form.Item>

              <Form.Item
                name="success_message"
                label="成功消息"
              >
                <Input placeholder="生成成功时显示的消息" />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={loading}>
                    保存配置
                  </Button>
                  <Button 
                    icon={<ExperimentOutlined />} 
                    onClick={testConnection}
                    loading={testLoading}
                  >
                    测试连接
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col span={8}>
          <Card title="测试功能">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button 
                type="primary" 
                onClick={generateTestImage}
                loading={generateLoading}
                block
              >
                生成测试图片
              </Button>
              
              {generateLoading && (
                <div style={{ textAlign: 'center', padding: '20px' }}>
                  <Spin size="large" />
                  <div style={{ marginTop: '10px' }}>
                    正在生成图片，请稍候...
                  </div>
                </div>
              )}
              
              {testImage && (
                <div>
                  <Text strong>测试结果：</Text>
                  <Image
                    src={testImage}
                    alt="测试图片"
                    style={{ width: '100%', marginTop: '10px' }}
                  />
                </div>
              )}
            </Space>
          </Card>

          <Card title="使用说明" style={{ marginTop: '16px' }}>
            <Alert
              message="使用方法"
              description={
                <div>
                  <p>在QQ中发送包含以下关键词的消息即可触发图像生成：</p>
                  <ul>
                    <li>画一只可爱的小猫</li>
                    <li>生成图片：美丽的风景</li>
                    <li>帮我生图，主题是星空</li>
                    <li>绘制一座宏伟的城堡</li>
                  </ul>
                  <p>系统会自动识别并生成相应的图片。</p>
                </div>
              }
              type="info"
              showIcon
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ImageGenPage;
