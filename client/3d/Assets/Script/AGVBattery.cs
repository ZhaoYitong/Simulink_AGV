using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class AGVBattery : MonoBehaviour
{
    public float m_BatteryConsumeSpeed;
    public float m_BatteryLeft = 100;

    private Vector3 m_LastPosition;
	
	void Start ()
    {
        m_LastPosition = transform.position;
	}
	
	void Update ()
    {
		if (transform.hasChanged)
        {
            float dis = (transform.position - m_LastPosition).sqrMagnitude;
            m_LastPosition = transform.position;
            m_BatteryLeft -= m_BatteryConsumeSpeed * dis;
        }
	}
}
