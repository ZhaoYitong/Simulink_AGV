using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Text;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

[Serializable]
public class PathData
{
    public int[] path;
    public float speed;
    public int flag;
}

[Serializable]
public class AGVManager
{

    public string m_Name;
    public string m_Address;
    public int m_Port;
    [HideInInspector] public GameObject m_Instance;

    private AGVMovement m_Movement;
    private AGVBattery m_Battery;
    private Socket m_Socket;
    private Thread m_RecvThread;
    private byte[] data = new byte[1024];

    public void Setup()
    {
        m_Movement = m_Instance.GetComponent<AGVMovement>();
        m_Movement.m_Manager = this;
        m_Battery = m_Instance.GetComponent<AGVBattery>();
        ConnectToServer();
    }

    public void OnPathComplete(int cell)
    {
        SendMsg(cell.ToString());
    }

    void ConnectToServer()
    {
        try
        {
            m_Socket = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
            m_Socket.Connect(IPAddress.Parse(m_Address), m_Port);
            Debug.Log(m_Name + "连接服务器成功");
            SendMsg("login " + m_Name);
            m_RecvThread = new Thread(ReceiveMsg);
            m_RecvThread.Start();

        }
        catch (System.Exception ex)
        {
            Debug.Log(m_Name + "连接服务器失败！");
            Debug.Log(ex.Message);
        }
    }

    private void ReceiveMsg()
    {
        while (true)
        {
            if (m_Socket.Connected == false)
            {
                Debug.Log(m_Name + "与服务器断开了连接");
                break;
            }

            Array.Clear(data, 0, data.Length);
            m_Socket.Receive(data);

            string result = Encoding.UTF8.GetString(data, 0, data.Length);
            Debug.Log(result);
            PathData path_data = JsonUtility.FromJson<PathData>(result);
            m_Movement.AddPath(path_data.path, path_data.speed);
            if (path_data.flag == 1)
            {
                m_Movement.flag = 1;
            }
            else
            {
                m_Movement.flag = 0;
            }
        }
    }

    public void SendMsg(string ms)
    {
        byte[] data = new byte[1024];
        data = Encoding.UTF8.GetBytes(ms);
        m_Socket.Send(data);
    }

    void OnDestroy()
    {
        try
        {
            if (m_Socket != null)
            {
                m_Socket.Shutdown(SocketShutdown.Both);
                m_Socket.Close();  //关闭连接
            }

            if (m_RecvThread != null)
            {
                m_RecvThread.Interrupt();
                m_RecvThread.Abort();
            }

        }
        catch (Exception ex)
        {
            Debug.Log(ex.Message);
        }
    }
}
