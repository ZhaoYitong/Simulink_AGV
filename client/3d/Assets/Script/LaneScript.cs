using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class LaneScript : MonoBehaviour {
    public void InitSize(float length, float width, ParameterScript.Direction direction)
    {
        float x1 = this.GetComponent<Renderer>().bounds.size.x;

        float z1 = this.GetComponent<Renderer>().bounds.size.z;

        float x2 = length;
        float z2 = width;
        float xScale = 1, zScale = 1;
        if (direction == ParameterScript.Direction.Horizontal)
        {
            xScale = x2 / x1;
            zScale = z2 / z1;
        }
        else if (direction == ParameterScript.Direction.Vertical)
        {
            xScale = z2 / x1;
            zScale = x2 / z1;
        }
        MeshFilter meshf = this.GetComponent<MeshFilter>();
        Mesh mesh = meshf.mesh;
        Vector3[] newVecs = new Vector3[mesh.vertices.Length];
        Vector3[] oldVecs = mesh.vertices;
        for (int i = 0; i < oldVecs.Length; i++)
        {
            newVecs[i].Set(oldVecs[i].x * xScale, oldVecs[i].y, oldVecs[i].z * zScale);
        }
        mesh.vertices = newVecs;
        mesh.RecalculateBounds();
    }
}
